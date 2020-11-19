tf2-express
===========

Automated trading bot for Team Fortress 2.

**NOTE: THIS BOT DOES NOT CURRENTLY WORK WITH ITEMS PRICED WITH KEYS**

Installation
------------
Download the repository, navigate to the folder, and install the required packages.

.. code-block:: text

    pip install -r requirements.txt 

Running
-------
Configurate the config.py and add your credentials.

.. code-block:: text

    python main.py

To open the GUI run this command and go to 127.0.0.1

.. code-block:: text

    python -m express.ui.panel

Features
--------
- Automatic pricing from Prices.TF
- Basic website GUI (going to be updated)
- Uses MongoDB for saving/getting prices and trades
- Supports both Non-Craftable and Craftable items
- Supports Random Craft Hats
- Supports options listed in settings.py
- Saves trade data after trade has gone through
- Colored and readable logging
- Bank as many items as you want

Backpack.tf listing might be added in the future.
