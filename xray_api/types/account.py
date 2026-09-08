from abc import ABC, abstractmethod 
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from ..proto.common.serial.typed_message_pb2 import TypedMessage
from ..proto.proxy.hysteria.account.config_pb2 import \
    Account as HysteriaAccountPb2
from ..proto.proxy.shadowsocks.config_pb2 import \
    Account as ShadowsocksAccountPb2
from ..proto.proxy.shadowsocks.config_pb2 import \
    CipherType as ShadowsocksCiphers
from ..proto.proxy.trojan.config_pb2 import Account as TrojanAccountPb2
from ..proto.proxy.vless.account_pb2 import Account as VLESSAccountPb2
from ..proto.proxy.vmess.account_pb2 import Account as VMessAccountPb2
from .message import Message


class Account(BaseModel, ABC):
    email: str
    level: int = 0

    @property
    @abstractmethod
    def message(self):
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.email}>"


class VMessAccount(Account):
    id: UUID

    @property
    def message(self):
        return Message(VMessAccountPb2(id=str(self.id)))


class XTLSFlows(Enum):
    NONE = ''
    VISION = 'xtls-rprx-vision'


class VLESSAccount(Account):
    id: UUID
    flow: XTLSFlows = XTLSFlows.NONE

    @property
    def message(self):
        return Message(VLESSAccountPb2(id=str(self.id), flow=self.flow.value))


class TrojanAccount(Account):
    password: str
    flow: XTLSFlows = XTLSFlows.NONE

    @property
    def message(self):
        return Message(TrojanAccountPb2(password=self.password))


class ShadowsocksMethods(Enum):
    AES_128_GCM = 'aes-128-gcm'
    AES_256_GCM = 'aes-256-gcm'
    CHACHA20_POLY1305 = 'chacha20-ietf-poly1305'


class ShadowsocksAccount(Account):
    password: str
    method: ShadowsocksMethods = ShadowsocksMethods.CHACHA20_POLY1305

    @property
    def cipher_type(self):
        return self.method.name

    @property
    def message(self):
        return Message(ShadowsocksAccountPb2(password=self.password, cipher_type=self.cipher_type))


class HysteriaAccount(Account):
    password: str

    @property
    def message(self):
        return Message(HysteriaAccountPb2(auth=self.password))


class WireGuardAccount(Account):
    private_key: str
    public_key: str

    @property
    def address(self) -> str:
        # Deterministic tunnel address derived from the DB user id embedded
        # at the start of "email" (Marzban encodes it as "{user_id}.{username}").
        # Marzban reserves 10.90.0.1 for the inbound's own interface address
        # (see XRayConfig._resolve_inbounds), so client addresses start at
        # 10.90.0.2 and wrap after roughly 65k users on a single inbound.
        try:
            user_id = int(self.email.split('.', 1)[0])
        except (ValueError, IndexError):
            user_id = 0
        host_part = (user_id + 1) & 0xFFFF
        return f"10.90.{(host_part >> 8) & 0xFF}.{host_part & 0xFF}"

    @property
    def message(self):
        # WireGuard peers are not managed through the HandlerService API;
        # they are baked into the inbound's static "peers" list instead.
        raise NotImplementedError("WireGuard users can't be added over the API, they require a core restart")
