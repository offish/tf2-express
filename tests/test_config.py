# from express.options import GlobalOptions, Options
# from express.utils import read_json_file


# def test_default_global_config() -> None:
#     config = read_json_file("./express/config.example.json")
#     options = GlobalOptions([])

#     options_keys = [option for option in options.__dataclass_fields__]
#     config_keys = [key for key in config]

#     # dont care about the order
#     options_keys.sort()
#     config_keys.sort()

#     assert options_keys == config_keys


# def test_default_config() -> None:
#     config = read_json_file("./express/config.example.json")
#     options = Options()

#     options_keys = [option for option in options.__dataclass_fields__]
#     config_keys = [key for key in config["bots"][0]["options"]]
#     # only first bot has all options

#     assert options_keys == config_keys
