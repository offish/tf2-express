from .database_provider import DatabaseProvider
from .json_store import JSON
from .mongodb import MongoDB

PROVIDERS = [MongoDB, JSON]


def get_database_provider(provider: str, username: str) -> DatabaseProvider:
    for i in PROVIDERS:
        if provider.lower() == i.__name__.lower():
            return i(username)

    raise ValueError(f"Unknown provider: {provider}")
