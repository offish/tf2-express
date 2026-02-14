import asyncio
import logging

from steam import TradeOffer

from ..exceptions import NoArbitrageModuleFound
from .base_manager import BaseManager

try:
    from ..ext.arbitrage import Arbitrage
except ImportError:
    Arbitrage = None


class ArbitrageManager(BaseManager):
    async def setup(self) -> None:
        if not self.options.arbitrage.enable:
            return

        if Arbitrage is None:
            raise NoArbitrageModuleFound("Arbitrage logic is not public")

        self.arbitrage = Arbitrage(self)
        await self.arbitrage.setup()

    def is_arbitrage_offer(
        self, their_items: list[dict], our_items: list[dict]
    ) -> bool:
        return self.arbitrage.is_arbitrage_offer(their_items, our_items)

    async def process_offer(
        self,
        trade: TradeOffer,
        their_items: list[dict],
        our_items: list[dict],
        offer_data: dict,
    ) -> None:
        await self.arbitrage.process_offer(trade, their_items, our_items, offer_data)

    async def after_offer_accepted(
        self, their_items: list[dict], our_items: list[dict]
    ) -> None:
        await self.arbitrage.after_offer_accepted(their_items, our_items)

    async def run(self) -> None:
        while True:
            logging.info("Looking for arbitrages...")
            await self.arbitrage.find_arbitrages()
            logging.info("Done looking for arbitrages")

            await asyncio.sleep(60)

    async def close(self) -> None:
        await self.arbitrage.close()
