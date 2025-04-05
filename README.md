# tf2-express
[![License](https://img.shields.io/github/license/offish/tf2-express.svg)](https://github.com/offish/tf2-express/blob/master/LICENSE)
[![Stars](https://img.shields.io/github/stars/offish/tf2-express.svg)](https://github.com/offish/tf2-express/stargazers)
[![Issues](https://img.shields.io/github/issues/offish/tf2-express.svg)](https://github.com/offish/tf2-express/issues)
[![Size](https://img.shields.io/github/repo-size/offish/tf2-express.svg)](https://github.com/offish/tf2-express)
[![Discord](https://img.shields.io/discord/467040686982692865?color=7289da&label=Discord&logo=discord)](https://discord.gg/t8nHSvA)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Automated TF2 trading bot with GUI support, built with Python. Prices are by default provided by [Prices.TF](https://prices.tf).

## Donate
Donations are not required, but greatly appericated.
- BTC: `bc1q9gmh5x2g9s0pw3282a5ypr6ms8qvuxh3fd7afh`
- [Steam Trade Offer](https://steamcommunity.com/tradeoffer/new/?partner=293059984&token=0-l_idZR)

## Features
* GUI for adding and changing items, prices, `max_stock` + browsing trades
* Supports automated price updates from [Prices.TF](https://prices.tf)
* Creates, modifies and deletes listings on [Backpack.TF](https://backpack.tf)
* Accepts incoming friend requests
* Supports buy/sell message commands (`sell_5021_6`)
* Sends counter offer when user is trying to take items for free
* Sends counter offer when values are incorrect
* Supports Random Craft Hats [[?]](#random-craft-hats)
* Bank as many items as you want
* Add items by either name or SKU
* Uses MongoDB for saving items, prices and trades
* Limited inventory fetching to mitigate rate-limits
* Supports 3rd party inventory providers [[?]](#3rd-party-inventory-providers)
* Supports 3rd party emitted "deals" [[?]](#3rd-party-deals)

All available options can be found [here](express/options.py).

**Key dependencies:**
* [steam.py](https://github.com/gobot1234/steam.py)
* [backpack-tf](https://github.com/offish/backpack-tf)
* [tf2-sku](https://github.com/offish/tf2-sku)
* [tf2-data](https://github.com/offish/tf2-data)
* [tf2-utils](https://github.com/offish/tf2-utils)

## Showcase
![GUI Showcase](https://github.com/user-attachments/assets/06f61b55-06a2-4bd7-a575-9225d68d2396)

## Installation
You need to have Python 3.10 or above installed.
If you want to run the bot using Docker see [Using Docker](#using-docker).

```bash
git clone git@github.com:offish/tf2-express.git
cd tf2-express
pip install -r requirements.txt
```

> [!NOTE]
> You need to host a MongoDB server for the bot to work. Download the free community version [here](https://www.mongodb.com/try/download/community). You may also want to install [MongoDB Compass](https://www.mongodb.com/products/tools/compass) to access/modify/delete collections  manually.

## Setup
> [!NOTE]
> Make a copy of `config.example.json` and name it `config.json`. Make sure it is in the same folder as the example file. Update credentials and set your preferred `options`.

Example config:
```json
{
    "bots": [
        {
            "username": "username",
            "password": "password",
            "api_key": "111AA1111AAAA11A1A11AA1AA1AAA111",
            "shared_secret": "Aa11aA1+1aa1aAa1a=",
            "identity_secret": "aA11aaaa/aa11a/aAAa1a1=",
            "options": {
                "use_backpack_tf": true,
                "backpack_tf_token": "token",
                "enable_deals": false,
                "inventory_provider": "steamsupply",
                "inventory_api_key": "mySteamSupplyApiKey",
                "accept_donations": true,
                "decline_trade_hold": true,
                "allow_craft_hats": true,
                "save_trade_offers": true,
                "owners": [
                    "76511111111111111",
                    "76522222222222222"
                ]
            }
        }
    ]
}
```

> [!NOTE]
> As of v3.0.0 tf2-express only supports running one bot instance at a time. It will use the first entry in `bots` in the config.

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

## Updating
```bash
# tf2-express/
git pull
pip install --upgrade -r requirements.txt
# update packages like bptf, tf2-utils, tf2-data and tf2-sku
# which the bot is dependant on
```

## Using Docker
First configure the bot like shown in [Setup](#setup).
Then change the timezone in the `Dockerfile`, it is set to use Oslo time by default.

```bash
make build # will build the tf2-express docker image and install dependencies
make run # will start mongodb and tf2-express
```

The GUI does not start automatically. To start the GUI run this:

```bash
make gui
```

The GUI will then be available at `http://127.0.0.1:5000`.

## Explanation
### Random Craft Hats
If a craftable hat does not have a specific price in the database, it will be viewed as a Random Craft Hat (SKU: -100;6), if `enable_craft_hats` is enabled. 

> [!CAUTION]
> This applies to any craftable unique hat, which includes hats such as The Team Captain, Earbuds, Max Heads etc. If these to not have their own price in the database, they will be priced as a Random Craft Hat, if this option is enabled.

Simply open the GUI and add "Random Craft Hat" to the pricelist. Set the buy and sell price to whatever you want. Random Craft Hats cannot get automatic price updates.

### 3rd Party Inventory Providers
Avoid Steam's inventory rate-limits by using a third party provider like SteamApis, Steam.Supply or your own.

### 3rd Party Deals
"Deals" in this context are data which is emitted by third party using a TCP socket. This data will be acted on, such as sending an offer using the included trade URL and price. They are named "deals" as I've been using it for arbitrage purposes.

> [!IMPORTANT]
> As of tf2-express v3.0.0 deals are currently broken.

## Testing
```bash
# tf2-express/
pytest
```

Every test should succeed except for the version check. The version needs to be incremented to pass this test.

## License
MIT License

Copyright (c) 2020-2025 offish ([confern](https://steamcommunity.com/id/confern))

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
