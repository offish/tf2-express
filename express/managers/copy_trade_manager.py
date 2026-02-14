from ..exceptions import NoModuleFound
from .base_manager import BaseManager

try:
    from ..ext.copy_trade import CopyTrade
except ImportError:
    CopyTrade = None


class CopyTradeManager(BaseManager):
    async def setup(self) -> None:
        if CopyTrade is None:
            raise NoModuleFound("Copy trade code is not public")

        self.copy_trade = CopyTrade(self)
        await self.copy_trade.setup()

    async def run(self) -> None:
        raise NotImplementedError
