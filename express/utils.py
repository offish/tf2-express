from math import floor, ceil

#from .etc.pricestf import get_schema

def get_steamid64(account_id: int) -> int:
    return 76561197960265728 + account_id


def to_refined(number: int) -> float:
    return float(floor(number / 9 * 100) / 100)


def to_scrap(number: float) -> int:
    return int(ceil(number * 9))


#def get_defindex(name: str) -> int:
#   schema = get_schema()
#
#    pass


class Items:
    def __init__(self, item: dict):
        self.item = item
        self.name = item['market_hash_name']
    #    self.marketable = item['marketable']

    def is_tf2(self) -> bool:
        return self.item['appid'] == 440

    def has_tag(self, tag) -> bool:
        for i in self.item['tags']:
            if i['localized_tag_name'] == tag:
                return True
        return False

    def has_name(self, name) -> bool:
        return self.name == name

    def has_description(self, description) -> bool:
        if 'descriptions' not in self.item:
            return False

        for i in self.item['descriptions']:
            if i['value'] == description:
                return True
        return False

    def is_craftable(self) -> bool:
        return not self.has_description('( Not Usable in Crafting )')

    def is_halloween(self) -> bool:
        return self.has_description('Holiday Restriction: Halloween / Full Moon')

    def is_craft_hat(self) -> bool:
        return self.is_craftable() \
            and not self.is_halloween() \
            and self.has_tag('Cosmetic')

    def is_key(self) -> bool:
        return self.is_craftable() \
            and self.has_name('Mann Co. Supply Crate Key')

    #def is_painted(self) -> bool:
    #    desc = self.item['descriptions']
    #
    #    for i in desc:
    #        if i['value'].startswith('Paint Color: '):
    #            return True
    #    return False

    #def get_paint(self) -> str:
    #    # Vil kaste error om gjennstanden ikke er painta
    #    # Retarda å ha is_painted innebygd her
    #    # Hvis den ikke har paint bør du expecte at den føkker seg
    #    desc = self.item['descriptions']
    #    paint = 'Paint Color: '
    #
    #    for i in desc:
    #        if i['value'].startswith(paint):
    #            return i['value'][len(paint):]
    #    return None

    def is_pure(self) -> bool:
        return self.is_craftable() \
            and (self.has_name('Refined Metal') \
            or self.has_name('Reclaimed Metal') \
            or self.has_name('Scrap Metal'))

    def get_pure(self) -> float:
        if self.has_name('Refined Metal'):
            return 1.00
        elif self.has_name('Reclaimed Metal'):
            return 0.33
        elif self.has_name('Scrap Metal'):
            return 0.11
        return 0.00

