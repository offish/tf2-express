from .settings import ALLOW_CRAFT_HATS


class Item:
    def __init__(self, item: dict) -> None:
        self.item = item
        self.name = item["market_hash_name"]

    def is_tf2(self) -> bool:
        return self.item["appid"] == 440

    def has_tag(self, tag: str, exact: bool = True) -> bool:
        for i in self.item["tags"]:
            item_tag = i["localized_tag_name"]
            if (item_tag == tag and exact) or (tag in item_tag.lower() and not exact):
                return True
        return False

    def has_name(self, name: str) -> bool:
        return self.name == name

    def in_description(self, description: str) -> bool:
        if not "descriptions" in self.item:
            return False

        for i in self.item["descriptions"]:
            if description in i["value"]:
                return True
        return False

    def has_description(self, description: str) -> bool:
        if not "descriptions" in self.item:
            return False

        for i in self.item["descriptions"]:
            if i["value"] == description:
                return True
        return False

    def is_craftable(self) -> bool:
        return not self.has_description("( Not Usable in Crafting )")

    def is_halloween(self) -> bool:
        return self.has_description("Holiday Restriction: Halloween / Full Moon")

    def is_craft_weapon(self) -> bool:
        return (
            self.has_tag("Unique")
            and self.has_tag("weapon", False)
            and self.is_craftable()
        )

    def is_craft_hat(self) -> bool:
        return (
            ALLOW_CRAFT_HATS
            and self.has_tag("Unique")
            and self.has_tag("Cosmetic")
            and self.is_craftable()
        )

    def is_unusual(self) -> bool:
        return (
            self.is_craftable()
            and self.has_tag("Unusual")
            and "Unusual " in self.name
            and self.in_description("★ Unusual Effect: ")
        )

    def is_unusual_cosmetic(self) -> bool:
        return self.is_unusual() and self.has_tag("Cosmetic")

    def get_effect(self) -> str:
        string = "★ Unusual Effect: "

        if not "descriptions" in self.item:
            return ""

        for i in self.item["descriptions"]:
            if string in i["value"]:
                return i["value"].replace(string, "")

        return ""

    def is_key(self) -> bool:
        return self.is_craftable() and self.has_name("Mann Co. Supply Crate Key")

    def is_pure(self) -> bool:
        return self.is_craftable() and (
            self.has_name("Refined Metal")
            or self.has_name("Reclaimed Metal")
            or self.has_name("Scrap Metal")
        )

    def get_pure(self) -> float:
        if self.has_name("Refined Metal"):
            return 1.00
        elif self.has_name("Reclaimed Metal"):
            return 0.33
        elif self.has_name("Scrap Metal"):
            return 0.11
        return 0.00
