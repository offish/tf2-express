from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..express import Express


class BaseManager:
    def __init__(self, client: "Express") -> None:
        self.client = client
        self.options = client.options
        self.database = client.database
        self.inventory_manager = client.inventory_manager
        self.listing_manager = client.listing_manager
        self.pricing_manager = client.pricing_manager
        self.discord_manager = client.discord_manager

    @property
    def name(self) -> str:
        return self.__class__.__name__.lower()

    async def setup(self) -> None:
        pass

    async def run(self) -> None:
        pass

    async def close(self) -> None:
        pass
