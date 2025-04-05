from typing import Any


def get_amount(amount_part: str) -> int | None:
    try:
        amount_part = amount_part.replace("x", "")
        return int(amount_part)
    except Exception:
        return None


def parse_command(command: str) -> dict[str, Any] | None:
    command = command.lower()
    parts = command.split("_")

    if len(parts) < 3:
        return

    intent = parts[0]
    amount_part = parts[1]
    has_amount_part = False

    amount = 1

    if "x" in amount_part:
        amount = get_amount(amount_part)

        if amount is not None:
            has_amount_part = True
        else:
            amount = 1

    sku_indexes = 2 if has_amount_part else 1
    sku_parts = parts[sku_indexes:]
    sku = ";".join(sku_parts)

    return {"intent": intent, "amount": amount, "sku": sku}
