import os
import json
from typing import List

from helpers import format_filename
import utils.config_utils as CU
from modules.combat import Loadout, CustomWeapon

CONFIG_FILENAME = format_filename("config.json")

STREAMER_LAYOUT_DEFAULT = {'layout': [
    [
        ['{}%', 'PERCENTAGE_RETURN', 'font-size: 20pt;']
    ],
    [
        ['Total Loots: {}', 'TOTAL_LOOTS'],
        ['Total Spend: {} PED', 'TOTAL_SPEND'],
        ['Total Return: {} PED', 'TOTAL_RETURN']
    ]], 'style': 'font-size: 12pt;'}

# Configuration class
class Config(object):
    # Version
    version = CU.ConfigValue(3)

    # Core Configuration
    location = CU.ConfigSecret("")
    name = CU.ConfigValue("")
    theme = CU.ConfigValue("dark")

    # Screenshot Configuration
    screenshot_directory = CU.ConfigValue("~/Documents/Globals/")
    screenshot_delay = CU.ConfigValue(500)
    screenshot_threshold = CU.ConfigValue(0)
    screenshot_enabled = CU.ConfigValue(True)

    # Combat Configuration
    loadouts: List[Loadout] = CU.ConfigValue([], type=Loadout)
    selected_loadout: Loadout = CU.ConfigValue(None, type=Loadout)
    custom_weapons: List[CustomWeapon] = CU.ConfigValue(None)

    # Streaming and Twitch
    streamer_layout = CU.JsonConfigValue(STREAMER_LAYOUT_DEFAULT)

    twitch_prefix = CU.ConfigValue("!")
    twitch_token = CU.ConfigValue("oauth:")
    twitch_username = CU.ConfigValue("NannyBot")
    twitch_channel = CU.ConfigValue("")
    twitch_commands_enabled = CU.ConfigValue(None)

    def __init__(self):
        # Initialize mutable options
        self.initialized = False
        self.loadouts = []
        self.custom_weapons = []
        self.twitch_commands_enabled = ["commands", "allreturns", "toploots", "info"]

        self.load_config()
        self.print()
        self.initialized = True

    def load_config(self):
        """
        Load the configuration from a file and update the object attributes accordingly.

        Returns:
            None
        """
        if not os.path.exists(CONFIG_FILENAME):
            return

        try:
            with open(CONFIG_FILENAME, 'r') as f:
                CONFIG = json.loads(f.read())
        except:
            config_contents = ""
            print("Empty Config")
            return

        if CONFIG.get("version", 1) < self.version.value:
            fn_name = "version_{}_to_{}".format(CONFIG.get("version", 1), self.version.value)
            CONFIG = getattr(CU, fn_name)(CONFIG)

        for item, value in CONFIG.items():

            if item == "loadouts":
                loadouts = []
                for data in value:
                    if isinstance(data, list):
                        loadouts.append(Loadout(**dict(zip(Loadout.FIELDS, data))))
                    else:
                        loadouts.append(Loadout(**data))

                value = loadouts
            elif item == "selected_loadout":
                if isinstance(value, list):
                    value = Loadout(**dict(zip(Loadout.FIELDS, value)))
                else:
                    value = Loadout(**value)
                    #changed so it works on linux ubuntu as well 
            """elif item == "selected_loadout":
                if isinstance(data, list):
                    value = Loadout(**dict(zip(Loadout.FIELDS, data)))
                else:
                    value = Loadout(**value)"""

            setattr(self, item, value)

    def dump(self) -> dict:
        """
        Returns a dictionary representation of the current object.

        :return: A dictionary containing the attributes of the current object.
        :rtype: dict
        """
        p = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            if attr_name == "loadouts":
                p[attr_name] = [loadout.dump() for loadout in attr.value]

            elif attr_name == "selected_loadout":
                p[attr_name] = attr.value.dump() if attr.value else {}

            elif isinstance(attr, CU.ConfigValue):
                p[attr_name] = attr.value
        return p

    def print(self):
        
        print(json.dumps(self.dump(), sort_keys=True, indent=4))

    def save(self):
        """
        Saves the current configuration to a file.

        This function checks if the instance has been initialized before saving the configuration. If the instance has not been initialized, the function returns without doing anything.

        The function converts the configuration data to a JSON string using the `json.dumps` function with indentation of 2 and sorted keys. It then writes the JSON string to a file specified by the `CONFIG_FILENAME` constant.

        If an error occurs during the saving process, an error message is printed to the console.

        Parameters:
            self: The instance of the class.

        Returns:
            None
        """
        if not self.initialized:
            return
        try:
            to_save = json.dumps(self.dump(), indent=2, sort_keys=True)
            with open(CONFIG_FILENAME, 'w') as f:
                f.write(to_save)
        except:
            print("Error saving config!")

    def __setattr__(self, item, value):
        """
        Set the value of an attribute.

        Args:
            item (str): The name of the attribute.
            value (Any): The value to set.

        Returns:
            None
        """
        print("Setting", item, value)
        if not isinstance(getattr(self, item, None), CU.ConfigValue):
            return super().__setattr__(item, value)
        config_item: CU.ConfigValue = getattr(self, item)
        config_item._value = value
        self.save()

