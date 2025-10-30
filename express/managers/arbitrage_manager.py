import asyncio
import logging
from typing import Any

from steam import TradeOffer

from ..exceptions import NoArbitrageModuleFound
from .base_manager import BaseManager

try:
    from ..arbitrage.arbitrage import Arbitrage
except ImportError:
    Arbitrage = None


class ArbitrageManager(BaseManager):
    def setup(self) -> None:
        if not (
            self.options.enable_arbitrage
            or self.options.enable_quickbuy
            or self.options.enable_quicksell
        ):
            return

        if Arbitrage is None:
            raise NoArbitrageModuleFound("Arbitrage logic is not public")

        self.arbitrage = Arbitrage(self)

    def is_arbitrage_offer(
        self, their_items: list[dict], our_items: list[dict]
    ) -> bool:
        return self.arbitrage.is_arbitrage_offer(their_items, our_items)

    async def quickbuy(self, skus: list[str]) -> None:
        if not self.options.enable_quickbuy:
            return

        return await self.arbitrage.quickbuy(skus)

    async def quicksell(self, skus: list[str]) -> None:
        if not self.options.enable_quicksell:
            return

        return await self.arbitrage.quicksell(skus)

    async def process_offer(
        self, trade: TradeOffer, their_items: list[dict], our_items: list[dict]
    ) -> None:
        return await self.arbitrage.process_offer(trade, their_items, our_items)

    async def process_offer_state(
        self, trade: TradeOffer, their_items: list[Any], our_items: list[Any]
    ) -> None:
        return await self.arbitrage.process_offer_state(trade, their_items, our_items)

    async def begin(self) -> None:
        await self.arbitrage.setup()

    async def run(self) -> None:
        while True:
            logging.info("Looking for arbitrage deals...")
            await self.arbitrage.find()
            logging.info("Done looking for deals")

            await asyncio.sleep(60)
