# tf2-express
Automated trading bot for Team Fortress 2. Prices are provided by [Prices.tf](https://prices.tf).

**THIS BOT DOES CURRENTLY NOT WORK FOR ITEMS PRICED WITH KEYS**

## Features
* Automatic pricing from [Prices.tf](https://prices.tf)
* Basic website GUI (going to be updated)
* Uses MongoDB for saving/getting prices and trades
* Run multiple bots at once
* Supports both Non-Craftable and Craftable items
* Supports Random Craft Hats
* Supports options listed in `settings.py`
* Saves trade data after trade has gone through
* Colored and readable logging
* Bank as many items as you want

Backpack.tf listing might be added in the future.

## Screenshot
![Screenshot](https://user-images.githubusercontent.com/30203217/99878862-a2587a00-2c08-11eb-9211-8c8ac86821e6.png)

## Installation
Download the repository, navigate to the folder, and install the required packages.

```
pip install -r requirements.txt 
```

## Setup
Configure the `bots` variable inside the `config.py` file under `express` folder. Here you need to add your bots credentials.

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

You can also change your settings inside the `settings.py` which is also under `express` folder. Every option or setting here should be pretty self explanatory.

```python
accept_donations    = True
decline_trade_hold  = True
decline_scam_offers = True
allow_craft_hats    = True
save_trades         = True

craft_hat_buy       = 1.55
craft_hat_sell      = 1.66
```


## Running
After you have configured the bot you can run this command. Make sure you're in the correct directory.
```
python main.py
```

To open the GUI run this command while being in the same directory as the `main.py` file, and open http://127.0.0.1:5000 in your browser.
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
