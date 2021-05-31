# tf2-express
[![License](https://img.shields.io/github/license/offish/tf2-express.svg)](https://github.com/offish/tf2-express/blob/master/LICENSE)
[![Stars](https://img.shields.io/github/stars/offish/tf2-express.svg)](https://github.com/offish/tf2-express/stargazers)
[![Issues](https://img.shields.io/github/issues/offish/tf2-express.svg)](https://github.com/offish/tf2-express/issues)
[![Size](https://img.shields.io/github/repo-size/offish/tf2-express.svg)](https://github.com/offish/tf2-express)
[![Discord](https://img.shields.io/discord/467040686982692865?color=7289da&label=Discord&logo=discord)](https://discord.gg/t8nHSvA)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![Donate Steam](https://img.shields.io/badge/donate-steam-green.svg)](https://steamcommunity.com/tradeoffer/new/?partner=293059984&token=0-l_idZR)
[![Donate PayPal](https://img.shields.io/badge/donate-paypal-blue.svg)](https://www.paypal.me/0ffish)

Automated trading bot for Team Fortress 2 using prices provided by [Prices.TF](https://prices.tf).

## Features
* Automatic pricing from [Prices.TF](https://prices.tf)
* Basic website GUI (going to be updated)
* Uses MongoDB for saving/getting prices and trades
* Support for running multiple bots at once
* Accepts offer(s) sent by owner
* Supports both Non-Craftable and Craftable items
* Supports Random Craft Hats
* Supports options listed in [`settings.py`](express/settings.py)
* Saves trade data after trade has gone through
* Colored and readable logging
* Bank as many items as you want

Backpack.tf listing might be added in the future.

## Screenshots
![GUI](https://user-images.githubusercontent.com/30203217/120229592-c2b76000-c24d-11eb-8d23-725556925ba3.png)
![Screenshot](https://user-images.githubusercontent.com/30203217/99878862-a2587a00-2c08-11eb-9211-8c8ac86821e6.png)

## Installation
Download the repository, navigate to the folder, and install the required packages.

```
pip install -r requirements.txt 
```

## Setup
Configure the `bots` variable inside the [`config.py`](express/config.py) file. Here you need to add your bots credentials.

```json
{
    "name": "Bot 1",
    "username": "steam-username",
    "password": "steam-password",
    "api_key": "api-key",
    "secrets": {
        "steamid": "steam-id-64",
        "shared_secret": "sharedsecret=",
        "identity_secret": "identitysecret="
    }
},
{
    "name": "Bot 2",
    "username": "steam-username",
    "password": "steam-password",
    "api_key": "api-key",
    "secrets": {
        "steamid": "steam-id-64",
        "shared_secret": "sharedsecret=",
        "identity_secret": "identitysecret="
    }
}
```
If you're running multiple bots, the variable should look something like this. `Name` is only for logging, this could be whatever you want (username, index, symbol, etc).

You can also change your settings inside the [`settings.py`](express/settings.py) file. 
Every option/setting here should be pretty self explanatory.

```python
accept_donations    = True
decline_trade_hold  = True
decline_scam_offers = True
allow_craft_hats    = True
save_trades         = True
```


## Running
After you have configured the bot you can run this command. Make sure you're in the correct directory.
```
python main.py
```

To open the GUI run this command while being in the same directory as the [`main.py`](main.py) file, and open http://127.0.0.1:5000 in your browser.
```
python -m express.ui.panel
```

## License
MIT License

Copyright (c) 2020 [offish](https://offi.sh)

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
