import logging
import json

import requests


def get_config() -> dict:
    config = {}

    with open("./express/config.json", "r") as f:
        config = json.loads(f.read())

    return config


def summarize_items(items: list[dict]) -> dict:
    summary = {}

    for item in items:
        item_name = items[item]["market_hash_name"]

        if item_name not in summary:
            summary[item_name] = {"count": 1, "image": items[item]["icon_url"]}
        else:
            summary[item_name]["count"] += 1

    return summary


def summarize_trades(trades: list[dict]) -> list[dict]:
    summary = []

    for trade in trades:
        their_items_summary = summarize_items(trade.get("their_items", []))
        our_items_summary = summarize_items(trade.get("our_items", []))

        summary.append(
            {
                **trade,
                "our_summary": our_items_summary,
                "their_summary": their_items_summary,
            }
        )

    return summary


def get_version(repository: str, folder: str) -> str:
    url = f"https://raw.githubusercontent.com/offish/{repository}/master/{folder}/__init__.py"

    r = requests.get(url)
    data = r.text

    version_index = data.index("__version__")
    start_quotation_mark = data.index('"', version_index)
    end_quotation_mark = data.index('"', start_quotation_mark + 1)

    # get rid of first "
    return data[start_quotation_mark + 1 : end_quotation_mark]


class ExpressFormatter(logging.Formatter):
    _format = "tf2-express | %(asctime)s - [%(levelname)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: _format,
        logging.INFO: _format,
        logging.WARNING: _format,
        logging.ERROR: _format + "(%(filename)s:%(lineno)d)",
        logging.CRITICAL: _format + "(%(filename)s:%(lineno)d)",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


class ExpressFileFormatter(logging.Formatter):
    _format = "%(filename)s %(asctime)s - [%(levelname)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: _format,
        logging.INFO: _format,
        logging.WARNING: _format,
        logging.ERROR: _format + "(%(filename)s:%(lineno)d)",
        logging.CRITICAL: _format + "(%(filename)s:%(lineno)d)",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%d/%m/%Y %H:%M:%S")
        return formatter.format(record)
