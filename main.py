from multiprocessing import Process, Pool
from time import sleep, time

from express.database import get_items
from express.logging import Log
from express.prices import update_pricelist
from express.client import Express
from express.config import BOTS


# import socketio
log = Log()


def run(bot: dict) -> None:
    client = Express(bot)

    try:
        client.login()
        client.run()

    except BaseException as e:
        log.info(f"Caught {type(e).__name__}")
        log.error(e)

        client.logout()

        log.info(f"Stopped")


def database() -> None:
    try:
        items_in_database = get_items()
        # log = Log()

        while True:
            if not items_in_database == get_items():
                log.info("Item(s) were added or removed from the database")
                items_in_database = get_items()
                update_pricelist(items_in_database)
                log.info("Successfully updated all prices")
            sleep(10)

    except BaseException:
        pass


if __name__ == "__main__":
    t1 = time()
    # log = Log()

    """try:
        socket = socketio.Client()

        items = get_items()
        # make own process with is_ready
        update_pricelist(items)
        log.info("Successfully updated all prices")

        del items

        @socket.event
        def connect():
            socket.emit("authentication")
            log.info("Successfully connected to Prices.TF socket server")

        @socket.event
        def authenticated(data):
            pass

        @socket.event
        def price(data):
            if data["name"] in get_items():
                update_price(data["name"], True, data["buy"], data["sell"])

        @socket.event
        def unauthorized(sid):
            pass

        socket.connect("https://api.prices.tf")
        log.info("Listening to Prices.TF for price updates")"""

    # try:
    process = Process(target=database)
    process.start()

    with Pool(len(BOTS)) as p:
        p.map(run, BOTS)

    # except BaseException as e:
    #     if e:
    #         log.error(e)

    # finally:
    #     t2 = time()
    #     log.info(f"Done. Bot ran for {round((t2-t1) / 60, 1)} minutes")
    #     log.close()
    #     quit()
    #     process.terminate()

"""    except BaseException as e:
        if e:
            log.error(e)

    finally:
        # socket.disconnect()
        t2 = time()
        log.info(f"Done. Bot ran for {round((t2-t1) / 60, 1)} minutes")
        log.close()
        quit()
"""
