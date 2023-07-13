from collections import namedtuple
import json
import os
from decimal import Decimal

from helpers import format_filename


MARKUP_FILENAME = format_filename("markup.json")


Markup = namedtuple("MarkupItem", ["value", "is_absolute"])
DEFAULT_NULL_MARKUP = Markup(Decimal("1.0"), False)

DEFAULT_MARKUP = {
    "Shrapnel": Markup(Decimal("1.01"), False),
}


class MarkupStore(object):

    def __init__(self):
        self._data = DEFAULT_MARKUP
        self.load_markup()

    def load_markup(self):
        """
        Load the markup data from the MARKUP_FILENAME file and update the _data dictionary.
        
        This function first checks if the MARKUP_FILENAME file exists. If it doesn't, the function returns without performing any action.
        
        If the file exists, the function opens it in read mode and attempts to load the content as JSON data using the json.loads() method. If an exception occurs during the loading process, the function assigns the DEFAULT_MARKUP value to the variable 'd'.
        
        After loading the JSON data or assigning the default value, the function iterates through each key-value pair in 'd' using a for loop. For each key-value pair, the function creates a new Markup object with the decimal value from the first element of the value tuple and the second element of the value tuple. The newly created Markup object is then added to the '_data' dictionary with the key 'k'.
        """
        if not os.path.exists(MARKUP_FILENAME):
            return
        with open(MARKUP_FILENAME, 'r') as f:
            try:
                d = json.loads(f.read())
            except:
                d = DEFAULT_MARKUP
            for k, v in d.items():
                self._data[k] = Markup(Decimal(v[0]), v[1])

    def save_markup(self):
        """
        Saves the markup data to a file.

        This function writes the markup data stored in the `_data` dictionary to a file named MARKUP_FILENAME. The markup data is serialized as a JSON object.

        Parameters:
            self (object): The instance of the class calling the function.

        Returns:
            None
        """
        with open(MARKUP_FILENAME, 'w') as f:
            f.write(json.dumps({k: [str(v[0]), v[1]] for k, v in self._data.items()}))

    def get_markup_for_item(self, name):
        """
        Retrieves the markup data for a given item.

        Args:
            name (str): The name of the item.

        Returns:
            Markup: The markup data for the item, or the default null markup if the item is not found.
        """
        if name not in self._data:
            # Asynchronously fetch markup data from Wiki Bot
            #response = requests.get("https://api.markupbot.com/markup/{}".format(name))
            # Will hopefully look something like:
            # {
            #    "day": {"rate": "101.00%", "volume": "100.0"},
            #    "week": {"rate": "101.00%", "volume": "100.0"},
            #    "month": {"rate": "101.00%", "volume": "100.0"},
            #    "year": {"rate": "101.00%", "volume": "100.0"},
            #    "decade": {"rate": "101.00%", "volume": "100.0"},
            #}
            #return Markup(response["month"]["rate"], False)
            return DEFAULT_NULL_MARKUP
        else:
            return self._data[name]

    def add_markup_for_item(self, name, value):
        """
        Adds markup for an item.

        Args:
            name (str): The name of the item.
            value (str): The value of the item.

        Returns:
            None
        """
        if value.startswith("+"):
            markup = Markup(Decimal(value[1:]), True)
        else:
            if value.endswith("%"):
                markup = Markup(Decimal(value[:-1]) / 100, False)
            else:
                markup = Markup(Decimal(value), False)
        self._data[name] = markup
        self.save_markup()

    def get_formatted_markup(self, name):
        """
        Generates a formatted markup for the given item name.

        Parameters:
            name (str): The name of the item.

        Returns:
            str: The formatted markup for the item, either a percentage or an absolute value.
        """
        mu = self.get_markup_for_item(name)
        if mu.is_absolute:
            return "+{:.3f}".format(mu.value)
        else:
            return "{:.3f}%".format(mu.value * 100)

    def apply_markup_to_item(self, name, count: int, value: Decimal):
        """
        Apply markup to an item.

        Args:
            name (str): The name of the item.
            count (int): The count of the item.
            value (decimal.Decimal): The value of the item.

        Returns:
            decimal.Decimal: The updated value of the item after applying markup.
        """
        mu = self.get_markup_for_item(name)
        if mu.is_absolute:
            return value + (count * mu.value)
        else:
            return value * mu.value
