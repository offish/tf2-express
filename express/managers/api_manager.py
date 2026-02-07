import time

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .base_manager import BaseManager

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn": {"level": "CRITICAL"},
        "uvicorn.error": {"level": "CRITICAL"},
        "uvicorn.access": {"level": "CRITICAL"},
    },
}


class APIManager(BaseManager):
    async def setup(self) -> None:
        enable_arbitrage = self.client.options.arbitrage.enable

        if not enable_arbitrage:
            self.arbitrage = None
        else:
            self.arbitrage = self.client.arbitrage_manager.arbitrage

        self.app = FastAPI()
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:5010"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        router = APIRouter()

        @router.get("/api/v1/stats")
        async def get_stats() -> dict:
            inventory = self.inventory_manager.get_our_inventory()
            pricelist = self.database.get_pricelist()

            return {
                "stats": {
                    "uptime": time.time() - self.client.started_at,
                    "pricelist_count": len(pricelist),
                    "inventory_count": len(inventory),
                }
            }

        @router.get("/api/v1/inventory")
        async def get_inventory() -> dict:
            inventory = self.inventory_manager.get_our_inventory()
            return {"inventory": inventory}

        @router.get("/api/v1/arbitrages")
        async def get_arbitrages() -> dict:
            arbitrages = self.database.get_arbitrages()
            return {"arbitrages": arbitrages}

        @router.get("/api/v1/prices")
        async def get_prices(sku: str) -> dict:
            if not enable_arbitrage:
                return {"success": False}

            prices = await self.arbitrage.get_prices(sku)
            return {"success": True, "prices": prices}

        @router.post("/api/v1/buy_item")
        async def buy_item(sku: str, site: str = None) -> dict:
            if not enable_arbitrage:
                return {"success": False}

            result = await self.arbitrage.buy_item(sku, site)
            return {"success": True, "result": result}

        @router.post("/api/v1/sell_item")
        async def sell_item(sku: str, site: str = None) -> dict:
            if not enable_arbitrage:
                return {"success": False}

            result = self.arbitrage.sell_item(sku, site)
            return {"success": True, "result": result}

        @router.post("/api/v1/dump")
        async def dump(skus: list[str]) -> dict:
            if not enable_arbitrage:
                return {"success": False}

            result = await self.arbitrage.dump(skus)
            return {"success": True, "result": result}

        @router.post("/api/v1/wishlist")
        async def wishlist(skus: list[str]) -> dict:
            if not enable_arbitrage:
                return {"success": False}

            result = await self.arbitrage.wishlist(skus)
            return {"success": True, "result": result}

        self.app.include_router(router)

    async def run(self) -> None:
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=8010,
            # log_config=LOGGING_CONFIG,
        )
        server = uvicorn.Server(config)
        await server.serve()
