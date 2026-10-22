from abc import ABC, abstractmethod
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from ..proto.proxy.shadowsocks.config_pb2 import \
    Account as ShadowsocksAccountPb2
from ..proto.proxy.shadowsocks_2022.config_pb2 import \
    Account as Shadowsocks2022AccountPb2
from ..proto.proxy.vless.account_pb2 import Account as VLESSAccountPb2
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


class XTLSFlows(Enum):
    NONE = ''
    VISION = 'xtls-rprx-vision'


class VLESSAccount(Account):
    id: UUID
    flow: XTLSFlows = XTLSFlows.NONE

    @property
    def message(self):
        return Message(VLESSAccountPb2(id=str(self.id), flow=self.flow.value))


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


class Shadowsocks2022Account(Account):
    """A user of a multi-user Shadowsocks 2022 inbound. The cipher is set on
    the inbound itself; each user only has its own base64 key."""
    key: str

    @property
    def message(self):
        return Message(Shadowsocks2022AccountPb2(key=self.key))
