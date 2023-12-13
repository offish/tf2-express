# tf2-express
[![License](https://img.shields.io/github/license/offish/tf2-express.svg)](https://github.com/offish/tf2-express/blob/master/LICENSE)
[![Stars](https://img.shields.io/github/stars/offish/tf2-express.svg)](https://github.com/offish/tf2-express/stargazers)
[![Issues](https://img.shields.io/github/issues/offish/tf2-express.svg)](https://github.com/offish/tf2-express/issues)
[![Size](https://img.shields.io/github/repo-size/offish/tf2-express.svg)](https://github.com/offish/tf2-express)
[![Discord](https://img.shields.io/discord/467040686982692865?color=7289da&label=Discord&logo=discord)](https://discord.gg/t8nHSvA)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Automated <abbr title="Team Fortress 2">TF2</abbr> trading bot with GUI support, built with Python. Prices are by default provided by [Prices.TF](https://prices.tf).

## Donate
Donations are not required, but greatly appericated.
- BTC: `bc1qntlxs7v76j0zpgkwm62f6z0spsvyezhcmsp0z2`
- [Steam Trade Offer](https://steamcommunity.com/tradeoffer/new/?partner=293059984&token=0-l_idZR)


## Features
* Automated item pricing by [Prices.TF](https://prices.tf)
* GUI for adding items, changing prices and browsing trades
* Bank as many items as you want
* Add items by name or SKU
* Uses MongoDB for saving items, prices and trades
* Supports Random Craft Hats [[?]](#random-craft-hats)
* Run multiple bots at once, each with their own database
* Supports SKU item formats for ease of use
* Supports 3rd party inventory providers [[?]](#3rd-party-inventory-providers)
* Utilizes [tf2-sku](https://github.com/offish/tf2-sku)
* Utilizes [tf2-data](https://github.com/offish/tf2-data)
* Utilizes [tf2-utils](https://github.com/offish/tf2-utils)

*Backpack.tf listing is not supported yet.*

## Showcase
![GUI Showcase](https://github.com/offish/tf2-express/assets/30203217/3093be18-412d-4852-a9a1-270f2e16f194)
![tf2-express](https://github.com/offish/tf2-express/assets/30203217/c32d6c2e-b59d-4923-97e7-8ba7cf5f8640)

## Installation
Full installation guide can be found on the [wiki](https://github.com/offish/tf2-express/wiki).

If MongoDB is already installed, it should be fairly straight forward.

```bash
git clone git@github.com:offish/tf2-express.git
cd tf2-express
pip install -r requirements.txt
```

## Setup
Rename `config.example.json` to `config.json`. Update credentials and set your preferred `options`.

Example config:
```json
{
    "name": "nickname",
    "check_versions_on_startup": true,
    "bots": [
        {
            "name": "bot1",
            "username": "username",
            "password": "password",
            "api_key": "111AA1111AAAA11A1A11AA1AA1AAA111",
            "secrets": {
                "steamid": "76511111111111111",
                "shared_secret": "Aa11aA1+1aa1aAa1a=",
                "identity_secret": "aA11aaaa/aa11a/aAAa1a1="
            },
            "options": {
                "accept_donations": true,
                "decline_bad_offers": false,
                "decline_trade_hold": true,
                "decline_scam_offers": true,
                "allow_craft_hats": true,
                "save_trades": true,
                "poll_interval": 30,
                "owners": [
                    "76511111111111111",
                    "76522222222222222"
                ]
            }
        },
        {
            "name": "bot2",
            "username": "username2",
            "password": "password2",
            "api_key": "111AA1111AAAA11A1A11AA1AA1AAA111",
            "secrets": {
                "steamid": "76511111111111111",
                "shared_secret": "Aa11aA1+1aa1aAa1a=",
                "identity_secret": "aA11aaaa/aa11a/aAAa1a1="
            },
            "options": {
                "accept_donations": true,
                "decline_bad_offers": false,
                "decline_trade_hold": false,
                "decline_scam_offers": false,
                "allow_craft_hats": false,
                "save_trades": true,
                "poll_interval": 60,
                "database": "bot2database"
            }
        }
    ]
}
```

For more information follow the [wiki](https://github.com/offish/tf2-express/wiki).

## Running
```bash
# tf2-express/
python main.py # start the bot
python panel.py # start the gui
```

After starting the GUI, you can open http://127.0.0.1:5000/ in your browser. 

Logs will be available under `logs/express.log`. 
Level is set to DEBUG, so here you will be able to see every request etc. and more information than is shown in the terminal.

*Do NOT share this log file with anyone else before removing sensitive information. This will leak your `API_KEY` and more.*

## Updating
```bash
# tf2-express/
git pull
pip install --upgrade -r requirements.txt
# update packages like tf2-utils, tf2-data and tf2-sku,
# which the bot is dependant on
```

## Explanation
### Random Craft Hats
If a craftable hat does not have a specific price in the database, it will be viewed as a Random Craft Hat (SKU: -100;6), if `enable_craft_hats` is enabled. 

**WARNING:** *This applies to any hat. Such as Ellis' Cap, Team Captain, Earbuds, Max Heads etc. This is a feature, not a bug.*

Simply open the GUI and add "Random Craft Hat" to the pricelist. Set the buy and sell price to whatever you want. This item cannot get automatic price updates.

### 3rd Party Inventory Providers
Avoid Steam's inventory rate-limits by using a third party provider like SteamApis, Steam.supply or your own.

## Testing
```bash
# tf2-express/
python -m unittest
```

## Todo
- [ ] Add stock limits (in stock/max stock)
- [ ] Add BackpackTF listing

## License
MIT License

Copyright (c) 2020-2023 offish

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
