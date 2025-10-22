from typing import Any


def try_parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def get_amount(amount_part: str) -> int | None:
    amount_part = amount_part.replace("x", "")
    return try_parse_int(amount_part)


def try_parse_sku(parts: list[str]) -> bool:
    defindex = try_parse_int(parts[0])
    quality = try_parse_int(parts[1])
    return defindex is not None and quality is not None


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
    is_sku = try_parse_sku(sku_parts)
    data = {"intent": intent, "amount": amount, "is_sku": is_sku}

    if is_sku:
        sku = ";".join(sku_parts)
        return data | {"sku": sku}

    return data | {"item_name": "_".join(sku_parts)}
