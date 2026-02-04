from express.managers.listing_manager import ListingManager

from .mock.express import Express


async def test_listing_manager(client: Express) -> None:
    listing_manager = ListingManager(client)
    await listing_manager.setup()

    assert not listing_manager._is_ready
    assert await listing_manager.set_user_agent()
