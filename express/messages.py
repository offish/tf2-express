from dataclasses import dataclass


@dataclass
class Messages:
    send_offer: str = ""
    counter_offer: str = ""
