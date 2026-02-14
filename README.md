# tf2-express
[![License](https://img.shields.io/github/license/offish/tf2-express.svg)](https://github.com/offish/tf2-express/blob/master/LICENSE)
[![Stars](https://img.shields.io/github/stars/offish/tf2-express.svg)](https://github.com/offish/tf2-express/stargazers)
[![Issues](https://img.shields.io/github/issues/offish/tf2-express.svg)](https://github.com/offish/tf2-express/issues)
[![Size](https://img.shields.io/github/repo-size/offish/tf2-express.svg)](https://github.com/offish/tf2-express)
[![Discord](https://img.shields.io/discord/467040686982692865?color=7289da&label=Discord&logo=discord)](https://discord.gg/t8nHSvA)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Automated TF2 trading bot with automatic pricing and GUI support, built with Python. Prices are by default provided by [PriceDB.io](https://pricedb.io).

## Donate
- BTC: `bc1q9gmh5x2g9s0pw3282a5ypr6ms8qvuxh3fd7afh`
- [Steam Trade Offer](https://steamcommunity.com/tradeoffer/new/?partner=293059984&token=0-l_idZR)

## Features
* GUI for adding/changing items, prices and `max_stock` + browsing trades
* Add items by name or SKU [[?]](#adding-items)
* Supports automated price updates from [PriceDB.io](https://pricedb.io)
* Supports 3rd party pricing providers
* Creates, modifies and deletes listings on [Backpack.TF](https://backpack.tf)
* Accepts incoming friend requests
* Supports buy/sell message commands (`sell_5021_6` or `sell_mann_co_supply_crate_key`)
* AI specialized chat message for unrecognized commands
* Sends counter offer when user is trying to take items for free
* Sends counter offer when values are incorrect
* Supports Random Craft Hats [[?]](#random-craft-hats)
* Bank as many items as you want
* Uses MongoDB for saving items, prices and trades
* Supports 3rd party inventory providers [[?]](#3rd-party-inventory-providers)
* Supports arbitraging items from different trading sites [[?]](#arbitrage)
* Blacklist certain SteamIDs from trading
* Checks if trade partner is banned on [Backpack.TF](https://backpack.tf)

All options are available [here](express/options.py).

**Key dependencies:**
* [steam.py](https://github.com/gobot1234/steam.py)
* [tf2-utils](https://github.com/offish/tf2-utils)
* [backpack-tf](https://github.com/offish/backpack-tf)
* [tf2-sku](https://github.com/offish/tf2-sku)
* [tf2-data](https://github.com/offish/tf2-data)

## Showcase
![GUI Showcase](https://github.com/user-attachments/assets/06f61b55-06a2-4bd7-a575-9225d68d2396)

## Installation
You need to have Python 3.11 or above installed.
If you want to run the bot using Docker see [Using Docker](#using-docker).

```bash
git clone git@github.com:offish/tf2-express.git
cd tf2-express
pip install -r requirements.txt
```

> [!NOTE]
> If you want to use MongoDB as a database provider you need to host a MongoDB server for the bot to work. Download the free community version [here](https://www.mongodb.com/try/download/community). You may also want to install [MongoDB Compass](https://www.mongodb.com/products/tools/compass) to access/modify collections manually. If you are going to use JSON files as a database provider instead, skip this step.

## Setup
For all of the following files, make a copy of the `x.example.json` files and rename them to not include "example" (e.g. `config.json` instead of `config.example.json`).

### `config.json`
```json
{
    "password": "password"
}
```

> [!IMPORTANT]
> If you only provide your account's password you need to have an **unencrypted** `.maFile` in the same folder as the config is. If you don't want to use the maFile for whatever reason, you need to provide your config as shown below.

```json
{
    "password": "password",
    "username": "username",
    "shared_secret": "shared_secret=",
    "identity_secret": "identity_secret="
}
```

### `options.json`
Your config should be structured like the example shown below. Options which are not present will be set to use their default. All the defaults are specified [here](express/options.py).

```json
{
    "price_provider": "pricedb",
    "database_provider": "mongodb",
    "owners": [],
    "blacklist": [],
    "backpack_tf": {
        "enable": false,
        "access_token": "token",
        "api_key": "apikey",
        "check_bans": false,
        "use_item_name": true
    },
    "inventory": {
        "provider": "steamcommunity",
        "api_key": "",
        "retries": 5
    },
    "offers": {
        "accept_donations": true,
        "decline_trade_hold": true,
        "enable_craft_hats": false,
        "save_trades": true,
        "counter_wrong_values": false
    },
    "chat": {
        "enable": false,
        "accept_friends": false
    },
    "discord": {
        "enable": false,
        "token": "",
        "channel_id": "",
        "owner_ids": []
    }
}
```

#### General options
| Option | Default | Description |
|--------|---------|-------------|
|`price_provider`| `"pricedb"` | Pricing provider to use. If you want to use your own custom pricer, read [this](). |
|`database_provider`| `"mongodb"` | `MongoDB` or `JSON`, JSON will use local JSON files instead of a database. MongoDB is the default when using Docker. |
|`owners`| \[] | List of SteamID64s of owners. Bot will accept offers from owners regardless of other conditions. |
|`blacklist`| \[] | List of SteamID64s of blacklisted users. Bot will decline offers from users who are blacklisted, and will not send offers to these users either. |
|`check_updates`| `True` | Wheter to check for new versions of tf2-express on  on startup or not. |
|`groups`| \[] | List of group IDs for the bot to join. |
|`client_options`| \{} | Optional kwargs dictionary for [steam.py](https://github.com/gobot1234/steam.py) client options to override. |


#### `backpack_tf` options
| Option | Default | Description |
| --------------- | --------------------- | ----------------------------------- |
| `enable`        | `False`               | Enable Backpack.tf integration      |
| `access_token`  | `""`                  | Backpack.tf OAuth access token      |
| `api_key`       | `""`                  | Backpack.tf API key                 |
| `user_agent`    | `"Listing goin' up!"` | User-Agent string used for requests |
| `check_bans`    | `False`               | Check Backpack.tf user ban status   |
| `use_item_name` | `True`                | Use item name instead of SKU in listing details |


#### `inventory` options
| Option     | Default            | Description |
| ---------- | ------------------ |------------ |
| `provider` | `"steamcommunity"` | Inventory provider (e.g. `steamcommunity`, `steamsupply`, `expressload`) |
| `api_key`  | `""`               | API key for the inventory provider |
| `retries`  | `5`                | Number of max retries when fetching inventory |


#### `offers` options
| Option                      | Default | Description                                                      |
| --------------------------- | ------- | ---------------------------------------------------------------- |
| `enable_craft_hats`         | `False` | Enable random craft hats in offers                               |
| `accept_donations`          | `False` | Automatically accept donation offers                             |
| `counter_wrong_values`      | `False` | Counter offers with incorrect values                             |
| `decline_trade_hold`        | `True`  | Decline offers with trade holds                                  |
| `cancel_sent`           | `False` | Cancel sent offers after a delay                                 |
| `cancel_sent_after_seconds` | `300`   | Time before canceling sent offers (requires `cancel_sent` enabled) |
| `save_trades`               | `True`  | Save trade offers to database |


#### `chat` options
| Option           | Default | Description                          |
| ---------------- | ------- | ------------------------------------ |
| `enable`         | `False` | Enable processing of chat messages (the bot will never send messages over Steam no matter if this is on or off)  |
| `accept_friends` | `False` | Automatically accept friend requests |


#### `discord` options
| Option       | Default | Description                                     |
| ------------ | ------- | ----------------------------------------------- |
| `enable`     | `False` | Enable Discord integration                      |
| `token`      | `""`    | Discord bot token                               |
| `channel_id` | `""`    | Discord channel ID for messages                 |
| `owner_ids`  | `[]`    | List of Discord user IDs with owner permissions |


### `messages.json`
| Key | Description |
|-----|-------------|
|`send_offer`| Offer message when sending an offer. |
|`counter_offer`| Offer message when counter offering. |


## Running
```bash
# tf2-express/
python main.py # start the bot
python panel.py # start the gui
```

Now you can visit the GUI at http://127.0.0.1:5000/ 

Logs will be available under `logs/express.log`. 
Level is set to DEBUG, so here you will be able to see every request etc. and more information than is shown in the terminal.

> [!WARNING]
> Do NOT share your logs or config files with anyone before removing sensitive information. This might leak your `API_KEY` and more.

## Hosting
If you want to run the bot 24/7, even when your computer is off, you can use [DigitalOcean](https://www.digitalocean.com/?refcode=602c0165acd8&utm_campaign=Referral_Invite&utm_medium=Referral_Program) or another VPS cloud provider. DigitalOcean offers $200 in free credit for trying their products.

[![DigitalOcean Logo](https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%203.svg)](https://www.digitalocean.com/?refcode=602c0165acd8&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge)

## Updating
```bash
# tf2-express/
git pull
pip install --upgrade -r requirements.txt
# update packages like bptf, tf2-utils, tf2-data and tf2-sku which the bot is dependant on
```

## Using Docker
First configure the bot like shown in [Setup](#setup).
Then change the timezone in the `Dockerfile`, it is set to use Oslo time by default.

```bash
make freeze # will generate fresh requirements.lock.txt
make build # will build the tf2-express docker image and install dependencies
make run # will start mongodb and tf2-express
```

The GUI does not start automatically. To start the GUI run this:

```bash
make gui
```

The GUI will then be available at http://127.0.0.1:5000/

## Explanation
### Random Craft Hats
If a craftable hat does not have a specific price in the database, it will be viewed as a Random Craft Hat (SKU: `-100;6`), if `enable_craft_hats` is enabled. 

> [!CAUTION]
> This applies to any craftable unique hat, which includes hats such as The Team Captain, Earbuds, Max Heads etc. If these do not have their own price in the database, they will be priced as a Random Craft Hat, if this option is enabled. Be careful when using this option, as it can lead to unwanted trades.

Simply open the GUI and add "Random Craft Hat" or `-100;6` to the pricelist. Set the buy and sell price to whatever you want. Random Craft Hats cannot get automatic price updates.

### Adding Items
The bot supports adding items via the GUI by using either item names or SKUs. Example: `Uncraftable Tour of Duty Ticket` or `725;6;uncraftable` would add the same item (`725;6;uncraftable`).

> [!IMPORTANT]
> Adding by name is sometimes bugged. For items like `Strange Wrench` it would get the SKU `7;6`, this is wrong and applies to other default weapons aswell. The correct SKU would be `197;11`. This issue stems from how defindexes are handled in `tf2-data` and `tf2-utils`. If an added item has the wrong SKU - delete the item and add it again using the SKU and not the item name. To check if a SKU is correct you can go to the GUI, click on the item and open it on [Marketplace.TF](https://marketplace.tf). If the item has 0 previous sales, it is most likely wrong.

### Arbitrage
"Arbitraging is the process of taking advantage of a price difference between two or more markets". Prior to v3.0.0 this bot used to support arbitraging of items via  [`tf2-arbitrage`](https://github.com/offish/tf2-arbitrage). This support has now been removed. The bot still supports arbitraging of items, but the code and logic for this remains private for the time being.

### 3rd Party Inventory Providers
Steam can rate-limit inventory fetch requests if they are called too often. This can be avoided using a third party provider like SteamApis, Steam.Supply, Express-Load or your own. This is especially useful if you are running multiple bots.

> [!NOTE]
> If you want to use [Express-Load](https://express-load.com/) you can use the promo code `offish` to receive free credits and try out their API for free.

## Testing
```bash
# tf2-express/
pytest
```

Every test should succeed except for the version check. The version needs to be incremented to pass this test.
