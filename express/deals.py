from .utils import decode_data, encode_data, sku_to_item_data

from threading import Thread
import logging
import socket


class Deals:
    def __init__(self, express, enabled: bool = False) -> None:
        self.enabled = enabled

        if not enabled:
            return

        self.express = express
        self.inventory = self.express.inventory
        self.db = self.express.db

    def begin(self) -> None:
        if not self.enabled:
            return

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to the server
        server_address = ("localhost", 12345)

        try:
            self.socket.connect(server_address)
            logging.info("Connected to socket server")
        except ConnectionRefusedError:
            raise SystemExit("Server socket is not running")

        self.socket_thread = Thread(target=self.listen, daemon=True)
        self.socket_thread.start()

    def listen(self) -> None:
        logging.info("Listening for deals...")

        while True:
            data = self.socket.recv(1024)
            deals = decode_data(data)

            for deal in deals:
                # can be other types of messages
                if not deal.get("is_deal"):
                    continue

                sku = deal["sku"]
                logging.info(f"Got a deal for {sku=}")

                self.db.add_price(
                    **sku_to_item_data(sku),
                    buy=deal["buy_price"],
                    sell=deal["sell_price"],
                )

                self.add_deal(deal)

    def add_deal(self, deal: dict) -> None:
        self.db.add_deal(deal)

    def update_deal(self, deal: dict) -> None:

        self.db.update_deal(deal)

    def delete_deal(self, sku: str) -> None:
        self.db.delete_deal(sku)

    def get_deal(self, sku: str) -> dict:
        return self.db.get_deal(sku)

    def get_deals(self) -> list[dict]:
        return self.db.get_deals().copy()

    def update_deal_state(self, sku: str, intent: str) -> None:
        for deal in self.get_deals():
            if sku != deal["sku"]:
                continue

            deal[intent] = True
            self.update_deal(deal)

            intent_text = "bought" if intent == "is_bought" else "sold"
            logging.info(sku + " was {}".format(intent_text))

        if intent == "is_sold" and self.db.is_temporarily_priced(sku):
            logging.info(f"Deleting temporary price for {sku}")
            self.db.delete_price(sku)

    def process_deals(self) -> None:
        if not self.enabled:
            return

        for deal in self.get_deals():
            sell_requested = (
                deal.get("sell_requested", False) and "pricestf" != deal["sell_site"]
            )
            buy_requested = (
                deal.get("buy_requested", False) and "pricestf" != deal["buy_site"]
            )
            is_bought = deal.get("is_bought", False)
            is_sold = deal.get("is_sold", False)
            sku = deal["sku"]

            logging.info(
                f"{sku} {sell_requested=} {buy_requested=} {is_bought=} {is_sold=}"
            )

            # deal is completed
            if is_sold:
                logging.info(f"{sku} deal successfully completed!")
                self.delete_deal(deal["sku"])
                continue

            # NOTE: request tf2-arbitrage to buy/sell an item
            if not buy_requested:
                deal["request_buy"] = True
                logging.info(f"Requesting to buy {sku}")
                self.send(deal)

                deal["buy_requested"] = True
                self.update_deal(deal)
                continue

            if is_bought and not sell_requested and "sell_data" not in deal:
                deal["request_sell"] = True
                logging.info(f"Requesting to sell {sku}")

                asset_id = self.inventory.get_last_item_in_our_inventory(sku)["assetid"]
                deal["our_item"] = asset_id
                self.send(deal)

                deal["sell_requested"] = True
                self.update_deal(deal)
                continue

            # send offer to buy order
            if "buy_data" in deal:
                logging.info(f"Sending offer to buy {sku}")
                buy_data = deal["buy_data"]
                trade_url = buy_data["trade_url"]
                response = self.express.send_offer(trade_url, "buy", sku)

                if response.get("success"):
                    deal["buy_offer_sent"] = True
                    self.update_deal(deal)

            if "sell_data" in deal:
                if not is_bought:
                    logging.info(f"{sku} still not bought")
                    continue

                logging.info(f"Sending offer to sell {sku}")
                sell_data = deal["sell_data"]
                trade_url = sell_data["trade_url"]
                response = self.express.send_offer(trade_url, "sell", sku)

                if response.get("success"):
                    deal["sell_offer_sent"] = True
                    self.update_deal(deal)

                # response =
                # if response.get("success") set true to is_sold

    def send(self, data: dict) -> None:
        if not self.socket:
            logging.warning("Socket empty, could not send data")
            return

        logging.info(f"Sending data {data=}")

        self.socket.sendall(encode_data(data))
