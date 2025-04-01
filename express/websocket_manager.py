import asyncio
import json
import logging
from typing import TYPE_CHECKING

from websockets import connect
from websockets.exceptions import ConnectionClosedError, InvalidStatus

from .utils import swap_intent

if TYPE_CHECKING:
    from .express import Express


class WebSocketManager:
    def __init__(self, client: "Express") -> None:
        self.ws = None
        self.client = client
        self.options = client.options

        self._users_in_queue = set()

    def add_user_to_queue(self, steam_id: str) -> None:
        self._users_in_queue.add(steam_id)
        logging.debug(f"Added user {steam_id} to queue")

    def remove_user_from_queue(self, steam_id: str) -> None:
        self._users_in_queue.remove(steam_id)
        logging.debug(f"Removed user {steam_id} from queue")

    async def _send_ws_message(self, data: dict) -> None:
        message = json.dumps({"message": data})
        await self._ws.send(message)

    async def _on_incoming_site_trade(self, data: dict) -> None:
        logging.info("Got incoming site trade")

        message = data.get("message", {})

        message_type = message.get("message_type")
        asset_ids = message.get("asset_ids")
        trade_url = message.get("trade_url")
        steam_id = message.get("steam_id")
        intent = message.get("intent")
        intent = message.get("intent")

        if message_type != "initalize_trade":
            logging.debug(f"Got {message_type=} for {message=}")
            return

        if steam_id in self._users_in_queue:
            logging.debug(f"User {steam_id} is already in queue")

            await self._send_ws_message(
                {
                    "success": False,
                    "steam_id": steam_id,
                    "message_type": "queue",
                    "message": "You are already in the queue!",
                }
            )
            return

        self.add_user_to_queue(steam_id)

        await self._send_ws_message(
            {
                "success": True,
                "steam_id": steam_id,
                "message_type": "queue",
                "message": "Please wait while we process your offer!",
            }
        )

        swapped_intent = swap_intent(intent)
        offer_id = await self.client.trade_manager.send_offer_by_trade_url(
            trade_url, swapped_intent, asset_ids
        )

        if not offer_id:
            logging.warning(f"Could not send offer to {steam_id}")
            self.remove_user_from_queue(steam_id)

            await self._send_ws_message(
                {
                    "success": False,
                    "steam_id": steam_id,
                    "message_type": "trade",
                    "message": "Could not send offer",
                }
            )
            return

        await self._send_ws_message(
            {
                "success": True,
                "steam_id": steam_id,
                "message_type": "trade",
                "message": "Offer was sent",
                "offer_id": offer_id,
            }
        )
        self.client.pending_site_offers[str(offer_id)] = steam_id

    async def _connect_to_site_ws(self, uri: str) -> None:
        async with connect(uri) as websocket:
            logging.info("Connected to Site WebSocket!")

            self._ws = websocket

            while True:
                message = await websocket.recv()
                data = json.loads(message)

                await self._on_incoming_site_trade(data)

    async def listen(self) -> None:
        token = self.options.express_tf_token
        uri = self.options.express_tf_uri + token

        while True:
            try:
                await self._connect_to_site_ws(uri)
            except (
                InvalidStatus,
                ConnectionRefusedError,
                ConnectionClosedError,
                TimeoutError,
            ) as e:
                logging.error(f"Error connecting to websocket: {e}")

            await asyncio.sleep(60)
