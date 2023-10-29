from tf2_utils import Item as UtilsItem


class Item(UtilsItem):
    def __init__(self, item: dict) -> None:
        super().__init__(item)

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
