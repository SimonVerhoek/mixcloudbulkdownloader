from dataclasses import dataclass
from typing import Dict


@dataclass()
class MixcloudUser:
    key: str
    name: str
    pictures: Dict[str, str]
    url: str
    username: str


@dataclass()
class Cloudcast:
    name: str
    url: str
    user: MixcloudUser
