from unittest import TestCase

from express.options import Options, GlobalOptions
from express.utils import read_json_file


class TestDefaultConfig(TestCase):
    def test_default_global_config(self):
        config = read_json_file("./express/config.example.json")
        options = GlobalOptions([])

        options_keys = [option for option in options.__dataclass_fields__]
        config_keys = [key for key in config]

        # dont care about the order
        options_keys.sort()
        config_keys.sort()

        self.assertListEqual(options_keys, config_keys)

    def test_default_config(self):
        config = read_json_file("./express/config.example.json")
        options = Options()

        options_keys = [option for option in options.__dataclass_fields__]
        config_keys = [key for key in config["bots"][0]["options"]]
        # only first bot has all options

        self.assertListEqual(options_keys, config_keys)
