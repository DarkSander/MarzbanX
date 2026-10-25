import time
import traceback
from datetime import datetime

from app import app, logger, scheduler, xray
from app.db import GetDB, crud
from app.models.node import NodeStatus
from app.utils import alerts
from config import JOB_CORE_HEALTH_CHECK_INTERVAL
from xray_api import exc as xray_exc

# when the main core was found dead, to alert once per outage
_core_down_since = None
_shutting_down = False


def _check_main_core(config):
    global _core_down_since

    if xray.core.started:
        if _core_down_since is not None:
            alerts.core_restored("main", datetime.utcnow() - _core_down_since)
            _core_down_since = None
        return config

    # a restart from the panel briefly leaves the core stopped
    if xray.core.restarting or _shutting_down:
        return config

    if _core_down_since is None:
        _core_down_since = datetime.utcnow()
        with xray.core.get_logs() as logs:
            alerts.core_down("main", list(logs))

    if not config:
        config = xray.config.include_db_users()
    try:
        xray.core.restart(config)
    except Exception as e:
        logger.error(f"Unable to restart Xray core: {e}")
    return config


def core_health_check():
    config = None

    # main core
    config = _check_main_core(config)

    # nodes' core
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            try:
                assert node.started
                node.api.get_sys_stats(timeout=2)
            except (ConnectionError, xray_exc.XrayError, AssertionError):
                if not config:
                    config = xray.config.include_db_users()
                xray.operations.restart_node(node_id, config)

        if not node.connected:
            if not config:
                config = xray.config.include_db_users()
            xray.operations.connect_node(node_id, config)


@app.on_event("startup")
def start_core():
    logger.info("Generating Xray core config")

    start_time = time.time()
    config = xray.config.include_db_users()
    logger.info(f"Xray core config generated in {(time.time() - start_time):.2f} seconds")

    # main core
    logger.info("Starting main Xray core")
    try:
        xray.core.start(config)
    except Exception:
        traceback.print_exc()

    # nodes' core
    logger.info("Starting nodes Xray core")
    with GetDB() as db:
        dbnodes = crud.get_nodes(db=db, enabled=True)
        node_ids = [dbnode.id for dbnode in dbnodes]
        for dbnode in dbnodes:
            crud.update_node_status(db, dbnode, NodeStatus.connecting)

    for node_id in node_ids:
        xray.operations.connect_node(node_id, config)

    scheduler.add_job(core_health_check, 'interval',
                      seconds=JOB_CORE_HEALTH_CHECK_INTERVAL,
                      coalesce=True, max_instances=1)


@app.on_event("shutdown")
def app_shutdown():
    global _shutting_down
    _shutting_down = True
    logger.info("Stopping main Xray core")
    xray.core.stop()

    logger.info("Stopping nodes Xray core")
    for node in list(xray.nodes.values()):
        try:
            node.disconnect()
        except Exception:
            pass
