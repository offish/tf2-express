tf2-express
===========

Automated trading bot for Team Fortress 2.

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

Features
--------
- Supports both Non-Craftable and Craftable items
- Supports Random Craft Hats
- Automatically accepts donations
- Automatically declines one-sided trades with items only on our side
- Saves trade data after trade has gone through
- Colored and somewhat detailed/readable logging
- Price as many items as you want (manually for now, but will add support for prices.tf later)
- Pricelist uses Refined Metal as prices
