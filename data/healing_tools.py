import json
from decimal import Decimal
from helpers import resource_path

ALL_HEALING_TOOLS = {}
data_filename = resource_path("healing_tools.json")

with open(data_filename, 'r') as f:
    data = json.loads(f.read())
    for name, healing_tool_data in data.items():
        healing_tool_data["decay"] = Decimal(healing_tool_data["decay"])
        ALL_HEALING_TOOLS[name] = healing_tool_data

FIELDS = ("name", "type", "decay")

if __name__ == "__main__":
    import sys

    all_healing_tools = {}

    for fn in sys.argv[1:]:
        with open(fn, 'r') as f:
            header = True
            for line in f.readlines():
                if header:
                    header = False
                    continue
                try:
                    data = dict(zip(FIELDS, line.split(";")))
                    data["decay"] = Decimal(data["decay"] if data["decay"].strip() else "0.0")

                    all_healing_tools[data["name"]] = {
                        "type": data["type"],
                        "decay": str(data["decay"])
                    }

                except:
                    break

    if all_healing_tools:
        output = open(data_filename, 'w')
        output.write(json.dumps(all_healing_tools, indent=2, sort_keys=True))
