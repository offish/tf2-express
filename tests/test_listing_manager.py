from express.managers.listing_manager import ListingManager

from .mock.express import Express

listing_manager: ListingManager = None


def test_listing_manager_setup(client: Express) -> None:
    global listing_manager
    listing_manager = ListingManager(client)
    listing_manager.setup()

    assert not listing_manager._is_ready


def test_is_banned() -> None:
    assert not listing_manager.is_banned("76561198253325712")
    assert not listing_manager.is_banned("76561198828172881")
    assert listing_manager.is_banned("76561199505594824")


def test_set_user_agent() -> None:
    assert listing_manager.set_user_agent()
