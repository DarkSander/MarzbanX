from __future__ import annotations

import base64
import json
import logging
import secrets
from collections import defaultdict
from copy import deepcopy
from pathlib import PosixPath
from typing import Union

import commentjson
from sqlalchemy import func

from app.db import GetDB
from app.db import models as db_models
from app.models.proxy import (
    REMOVED_PROTOCOLS,
    SS2022_METHODS,
    VLESS_NETWORKS,
    ProxyTypes,
    decode_ss2022_key,
    ss2022_user_key,
)
from app.models.user import UserStatus
from app.utils.crypto import get_cert_SANs
from config import DEBUG, XRAY_EXCLUDE_INBOUND_TAGS, XRAY_FALLBACKS_INBOUND_TAG

logger = logging.getLogger("uvicorn.error")

# "0." keeps it parseable as "{user_id}.{username}"; no user has id 0
SS2022_PLACEHOLDER_EMAIL = "0.marzbanx-ss2022-placeholder"


def unsupported_inbound_reason(inbound: dict):
    """Why MarzbanX won't manage this inbound's users, or None if it will."""
    protocol = inbound.get('protocol')
    if protocol in REMOVED_PROTOCOLS:
        return f"protocol \"{protocol}\" is not supported, use VLESS or Shadowsocks"

    if protocol == ProxyTypes.VLESS.value:
        net = (inbound.get('streamSettings') or {}).get('network', 'tcp')
        if net not in VLESS_NETWORKS:
            return f"VLESS transport \"{net}\" is not supported, use RAW (TCP), XHTTP or gRPC"

    if protocol == ProxyTypes.Shadowsocks.value:
        settings = inbound.get('settings') or {}
        method = settings.get('method') or ''
        if method.startswith('2022-'):
            if method not in SS2022_METHODS:
                return (f"Shadowsocks method \"{method}\" doesn't support multiple users, "
                        f"use one of: {', '.join(SS2022_METHODS)}")
            size = SS2022_METHODS[method]
            if not decode_ss2022_key(settings.get('password') or '', size):
                return (f"settings.password must be a base64 key of {size} bytes for {method} "
                        "(use the key generator in Core Settings)")

    return None


def supports_xtls_flow(inbound: dict) -> bool:
    """XTLS Vision only works over RAW (TCP) with TLS or REALITY."""
    return (
        inbound.get('network', 'tcp') in ('tcp', 'raw')
        and inbound.get('tls') in ('tls', 'reality')
        and inbound.get('header_type') != 'http'
    )


def merge_dicts(a, b):  # B will override A dictionary key and values
    for key, value in b.items():
        if isinstance(value, dict) and key in a and isinstance(a[key], dict):
            merge_dicts(a[key], value)  # Recursively merge nested dictionaries
        else:
            a[key] = value
    return a


class XRayConfig(dict):
    def __init__(self,
                 config: Union[dict, str, PosixPath] = {},
                 api_host: str = "127.0.0.1",
                 api_port: int = 8080):
        if isinstance(config, str):
            try:
                # considering string as json
                config = commentjson.loads(config)
            except (json.JSONDecodeError, ValueError):
                # considering string as file path
                with open(config, 'r') as file:
                    config = commentjson.loads(file.read())

        if isinstance(config, PosixPath):
            with open(config, 'r') as file:
                config = commentjson.loads(file.read())

        if isinstance(config, dict):
            config = deepcopy(config)

        self.api_host = api_host
        self.api_port = api_port

        super().__init__(config)
        self._validate()

        self.inbounds = []
        self.inbounds_by_protocol = {}
        self.inbounds_by_tag = {}
        # tag -> reason, for inbounds the panel refuses to manage
        self.unsupported_inbounds = {}
        self._fallbacks_inbound = self.get_inbound(XRAY_FALLBACKS_INBOUND_TAG)
        self._resolve_inbounds()

        self._apply_api()

    def _apply_api(self):
        api_inbound = self.get_inbound("API_INBOUND")
        if api_inbound:
            api_inbound["listen"] = self.api_host
            api_inbound["listen"]["address"] = self.api_host
            api_inbound["port"] = self.api_port
            return

        self["api"] = {
            "services": [
                "HandlerService",
                "StatsService",
                "LoggerService"
            ],
            "tag": "API"
        }
        self["stats"] = {}
        forced_policies = {
            "levels": {
                "0": {
                    "statsUserUplink": True,
                    "statsUserDownlink": True
                }
            },
            "system": {
                "statsInboundDownlink": False,
                "statsInboundUplink": False,
                "statsOutboundDownlink": True,
                "statsOutboundUplink": True
            }
        }
        if self.get("policy"):
            self["policy"] = merge_dicts(self.get("policy"), forced_policies)
        else:
            self["policy"] = forced_policies
        inbound = {
            "listen": self.api_host,
            "port": self.api_port,
            "protocol": "dokodemo-door",
            "settings": {
                "address": self.api_host
            },
            "tag": "API_INBOUND"
        }
        try:
            self["inbounds"].insert(0, inbound)
        except KeyError:
            self["inbounds"] = []
            self["inbounds"].insert(0, inbound)

        rule = {
            "inboundTag": [
                "API_INBOUND"
            ],
            "outboundTag": "API",
            "type": "field"
        }
        try:
            self["routing"]["rules"].insert(0, rule)
        except KeyError:
            self["routing"] = {"rules": []}
            self["routing"]["rules"].insert(0, rule)

    def _validate(self):
        if not self.get("inbounds"):
            raise ValueError("config doesn't have inbounds")

        if not self.get("outbounds"):
            raise ValueError("config doesn't have outbounds")

        for inbound in self['inbounds']:
            if not inbound.get("tag"):
                raise ValueError("all inbounds must have a unique tag")
            if ',' in inbound.get("tag"):
                raise ValueError("character «,» is not allowed in inbound tag")
        for outbound in self['outbounds']:
            if not outbound.get("tag"):
                raise ValueError("all outbounds must have a unique tag")

    def _resolve_inbounds(self):
        for inbound in self['inbounds']:
            if inbound['tag'] in XRAY_EXCLUDE_INBOUND_TAGS:
                continue

            reason = unsupported_inbound_reason(inbound)
            if reason:
                self.unsupported_inbounds[inbound['tag']] = reason
                logger.warning(f"Inbound \"{inbound['tag']}\" is ignored by MarzbanX: {reason}")
                continue

            if not inbound['protocol'] in ProxyTypes._value2member_map_:
                continue

            if not inbound.get('settings'):
                inbound['settings'] = {}

            if not inbound['settings'].get('clients'):
                inbound['settings']['clients'] = []

            settings = {
                "tag": inbound["tag"],
                "protocol": inbound["protocol"],
                "port": None,
                "network": "tcp",
                "tls": 'none',
                "sni": [],
                "host": [],
                "path": "",
                "header_type": "",
                "is_fallback": False
            }

            # port settings
            try:
                settings['port'] = inbound['port']
            except KeyError:
                if self._fallbacks_inbound:
                    try:
                        settings['port'] = self._fallbacks_inbound['port']
                        settings['is_fallback'] = True
                    except KeyError:
                        raise ValueError("fallbacks inbound doesn't have port")

            # VLESS Encryption (post-quantum): the paired "encryption" string
            # for clients lives next to "decryption" in the inbound settings
            # as a Marzban-only bookkeeping field; Xray-core itself ignores it.
            if inbound['protocol'] == ProxyTypes.VLESS.value:
                encryption = inbound['settings'].get('encryption')
                if encryption:
                    settings['encryption'] = encryption

            # Shadowsocks 2022: the cipher and the server key are shared by
            # every user of the inbound, clients need both.
            if inbound['protocol'] == ProxyTypes.Shadowsocks.value:
                method = inbound['settings'].get('method') or ''
                if method in SS2022_METHODS:
                    settings['ss2022_method'] = method
                    settings['ss2022_server_key'] = inbound['settings']['password']

            # stream settings
            if stream := inbound.get('streamSettings'):
                net = stream.get('network', 'tcp')
                net_settings = stream.get(f"{net}Settings", {})
                security = stream.get("security")
                tls_settings = stream.get(f"{security}Settings")

                if settings['is_fallback'] is True:
                    # probably this is a fallback
                    security = self._fallbacks_inbound.get(
                        'streamSettings', {}).get('security')
                    tls_settings = self._fallbacks_inbound.get(
                        'streamSettings', {}).get(f"{security}Settings", {})

                settings['network'] = net

                if security == 'tls':
                    # settings['fp']
                    # settings['alpn']
                    settings['tls'] = 'tls'
                    for certificate in tls_settings.get('certificates', []):

                        if certificate.get("certificateFile", None):
                            with open(certificate['certificateFile'], 'rb') as file:
                                cert = file.read()
                                settings['sni'].extend(get_cert_SANs(cert))

                        if certificate.get("certificate", None):
                            cert = certificate['certificate']
                            if isinstance(cert, list):
                                cert = '\n'.join(cert)
                            if isinstance(cert, str):
                                cert = cert.encode()
                            settings['sni'].extend(get_cert_SANs(cert))

                elif security == 'reality':
                    settings['fp'] = 'chrome'
                    settings['tls'] = 'reality'
                    settings['sni'] = tls_settings.get('serverNames', [])

                    try:
                        settings['pbk'] = tls_settings['publicKey']
                    except KeyError:
                        pvk = tls_settings.get('privateKey')
                        if not pvk:
                            raise ValueError(
                                f"You need to provide privateKey in realitySettings of {inbound['tag']}")

                        try:
                            from app.xray import core
                            x25519 = core.get_x25519(pvk)
                            settings['pbk'] = x25519['public_key']
                        except ImportError:
                            pass

                        if not settings.get('pbk'):
                            raise ValueError(
                                f"You need to provide publicKey in realitySettings of {inbound['tag']}")

                    try:
                        settings['sids'] = tls_settings.get('shortIds')
                        settings['sids'][0]  # check if there is any shortIds
                    except (IndexError, TypeError):
                        raise ValueError(
                            f"You need to define at least one shortID in realitySettings of {inbound['tag']}")
                    try:
                        settings['spx'] = tls_settings.get('SpiderX')
                    except:
                        settings['spx'] = ""

                if net in ('tcp', 'raw'):
                    header = net_settings.get('header', {})
                    request = header.get('request', {})
                    path = request.get('path')
                    host = request.get('headers', {}).get('Host')

                    settings['header_type'] = header.get('type', '')

                    if isinstance(path, str) or isinstance(host, str):
                        raise ValueError(f"Settings of {inbound['tag']} for path and host must be list, not str\n"
                                         "https://xtls.github.io/config/transports/tcp.html#httpheaderobject")

                    if path and isinstance(path, list):
                        settings['path'] = path[0]

                    if host and isinstance(host, list):
                        settings['host'] = host

                elif net == 'grpc' or net == 'gun':
                    settings['header_type'] = ''
                    settings['path'] = net_settings.get('serviceName', '')
                    host = net_settings.get('authority', '')
                    settings['host'] = [host]
                    settings['multiMode'] = net_settings.get('multiMode', False)

                elif net in ('splithttp', 'xhttp'):
                    settings['path'] = net_settings.get('path', '')
                    host = net_settings.get('host', '')
                    settings['host'] = [host]
                    settings['scMaxEachPostBytes'] = net_settings.get('scMaxEachPostBytes', 1000000)
                    settings['scMaxConcurrentPosts'] = net_settings.get('scMaxConcurrentPosts', 100)
                    settings['scMinPostsIntervalMs'] = net_settings.get('scMinPostsIntervalMs', 30)
                    settings['xPaddingBytes'] = net_settings.get('xPaddingBytes', "100-1000")
                    settings['xmux'] = net_settings.get('xmux', {})
                    settings["mode"] = net_settings.get("mode", "auto")
                    settings["noGRPCHeader"] = net_settings.get("noGRPCHeader", False)
                    settings["keepAlivePeriod"] = net_settings.get("keepAlivePeriod", 0)

            self.inbounds.append(settings)
            self.inbounds_by_tag[inbound['tag']] = settings

            try:
                self.inbounds_by_protocol[inbound['protocol']].append(settings)
            except KeyError:
                self.inbounds_by_protocol[inbound['protocol']] = [settings]

    def get_inbound(self, tag) -> dict:
        for inbound in self['inbounds']:
            if inbound['tag'] == tag:
                return inbound

    def get_outbound(self, tag) -> dict:
        for outbound in self['outbounds']:
            if outbound['tag'] == tag:
                return outbound

    def to_json(self, **json_kwargs):
        return json.dumps(self, **json_kwargs)

    def copy(self):
        return deepcopy(self)

    def include_db_users(self) -> XRayConfig:
        config = self.copy()

        with GetDB() as db:
            query = db.query(
                db_models.User.id,
                db_models.User.username,
                func.lower(db_models.Proxy.type).label('type'),
                db_models.Proxy.settings,
                func.group_concat(db_models.excluded_inbounds_association.c.inbound_tag).label('excluded_inbound_tags')
            ).join(
                db_models.Proxy, db_models.User.id == db_models.Proxy.user_id
            ).outerjoin(
                db_models.excluded_inbounds_association,
                db_models.Proxy.id == db_models.excluded_inbounds_association.c.proxy_id
            ).filter(
                db_models.User.status.in_([UserStatus.active, UserStatus.on_hold])
            ).group_by(
                func.lower(db_models.Proxy.type),
                db_models.User.id,
                db_models.User.username,
                db_models.Proxy.settings,
            )
            result = query.all()

            grouped_data = defaultdict(list)

            for row in result:
                grouped_data[row.type].append((
                    row.id,
                    row.username,
                    row.settings,
                    [i for i in row.excluded_inbound_tags.split(',') if i] if row.excluded_inbound_tags else None
                ))

            for proxy_type, rows in grouped_data.items():

                inbounds = self.inbounds_by_protocol.get(proxy_type)
                if not inbounds:
                    continue

                for inbound in inbounds:
                    resolved_settings = config.get_inbound(inbound['tag'])['settings']
                    clients = resolved_settings['clients']
                    ss2022_method = inbound.get('ss2022_method')

                    for row in rows:
                        user_id, username, settings, excluded_inbound_tags = row

                        if excluded_inbound_tags and inbound['tag'] in excluded_inbound_tags:
                            continue

                        if ss2022_method:
                            # the cipher is set on the inbound, users only have a key
                            clients.append({
                                "email": f"{user_id}.{username}",
                                "password": ss2022_user_key(settings['password'], ss2022_method),
                            })
                            continue

                        client = {
                            "email": f"{user_id}.{username}",
                            **settings
                        }

                        if client.get('flow') and not supports_xtls_flow(inbound):
                            del client['flow']

                        clients.append(client)

        # Xray-core builds a Shadowsocks 2022 inbound without clients as a
        # single-user server: it would then accept the server key alone
        # (which every user gets in their subscription) and refuse users
        # added later over the API. A placeholder user with a random key that
        # is never handed out keeps the inbound in multi-user mode.
        for inbound in self.inbounds:
            ss2022_method = inbound.get('ss2022_method')
            if ss2022_method:
                config.get_inbound(inbound['tag'])['settings']['clients'].append({
                    "email": SS2022_PLACEHOLDER_EMAIL,
                    "password": base64.b64encode(secrets.token_bytes(SS2022_METHODS[ss2022_method])).decode(),
                })

        if DEBUG:
            with open('generated_config-debug.json', 'w') as f:
                f.write(config.to_json(indent=4))

        return config
