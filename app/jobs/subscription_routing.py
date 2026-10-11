from app import scheduler
from app.utils import happ_routing

# Checks hourly but only downloads once a day (see happ_routing.refresh), so
# restarts and GitHub outages don't stretch the gap between updates.
scheduler.add_job(happ_routing.refresh, 'interval', coalesce=True, hours=1, max_instances=1)
