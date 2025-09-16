import asyncio
import logging

from steam import TradeOffer
from tf2_utils import get_sku, is_pure

from ..exceptions import NoArbitrageModuleFound
from .base_manager import BaseManager

try:
    from ..arbitrage.arbitrage import Arbitrage
except ImportError:
    Arbitrage = None


class ArbitrageManager(BaseManager):
    def setup(self) -> None:
        if not self.options.enable_arbitrage:
            return

        if Arbitrage is None:
            raise NoArbitrageModuleFound("Arbitrage functionality is not public")

        self.arbitrage = Arbitrage(self)

    def is_arbitrage_offer(
        self, their_items: list[dict], our_items: list[dict]
    ) -> bool:
        if not self.options.enable_arbitrage:
            return False

        arbitrages = self.database.get_arbitrages()

        if len(arbitrages) == 0:
            return False

        skus_in_offer = []

        for item in their_items + our_items:
            sku = get_sku(item)

            if not is_pure(sku):
                skus_in_offer.append(sku)

        if len(skus_in_offer) != 1:
            return False

        sku = skus_in_offer[0]

        for arbitrage in arbitrages:
            if sku == arbitrage["sku"]:
                return True

        return False

    async def process_offer(
        self, trade: TradeOffer, their_items: list[dict], our_items: list[dict]
    ) -> None:
        return await self.arbitrage.process_offer(trade, their_items, our_items)

    async def run(self) -> None:
        while True:
            logging.info("Looking for arbitrage deals...")
            await self.arbitrage.find()
            logging.info("Done. Schema was checked for deals")

            await asyncio.sleep(60)
