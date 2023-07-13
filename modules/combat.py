from collections import defaultdict, namedtuple
from datetime import datetime
import time
from typing import List
from decimal import Decimal
import threading
import os
import json


from modules.base import BaseModule
from chat import BaseChatRow, CombatRow, LootInstance, SkillRow, EnhancerBreakages, HealRow, GlobalInstance
from helpers import dt_to_ts, ts_to_dt, format_filename
from ocr import screenshot_window
from modules.markup import MarkupStore


RUNS_FILE = format_filename("runs.json")
RUNS_DIRECTORY = format_filename("")
MarkupSingleton = MarkupStore()


def take_screenshot(delay_ms, directory, glob: GlobalInstance):
    """
    :param glob:
    :return:
    """
    time.sleep(delay_ms / 1000.0)
    im, _, _ = screenshot_window()

    ts = time.mktime(glob.time.timetuple())
    screenshot_name = f"{glob.creature}_{glob.value}_{ts}.png"
    screenshot_fullpath = os.path.join(os.path.expanduser(directory), screenshot_name)
    im.save(screenshot_fullpath)


class Loadout(object):
    FIELDS = ("weapon", "amp", "scope", "sight_1", "sight_2", "damage_enh", "accuracy_enh", "economy_enh")

    def __init__(self, weapon: str = None, amp: str = None, scope: str = None, sight_1: str = None,
                 sight_2: str = None, damage_enh: int = 0, accuracy_enh: int = 0, economy_enh: int = 0):
        self.weapon = weapon
        self.amp = amp
        self.scope = scope
        self.sight_1 = sight_1
        self.sight_2 = sight_2
        self.damage_enh = damage_enh
        self.accuracy_enh = accuracy_enh
        self.economy_enh = economy_enh

    def __str__(self):
        """
        Return a string representation of the Loadout object.

        Returns:
            str: The string representation of the Loadout object.
        """
        contents = ", ".join([f"{field}={repr(getattr(self, field))}" for field in self.FIELDS])
        return f"Loadout({contents})"

    def dump(self):
        """
        Returns a dictionary containing the attributes of the weapon object.

        Returns:
            dict: A dictionary containing the following attributes of the weapon object:
                - weapon (str): The weapon type.
                - amp (float): The amplification value.
                - scope (str): The scope type.
                - sight_1 (str): The first sight type.
                - sight_2 (str): The second sight type.
                - damage_enh (bool): Indicates if damage enhancement is enabled.
                - accuracy_enh (bool): Indicates if accuracy enhancement is enabled.
                - economy_enh (bool): Indicates if economy enhancement is enabled.
        """
        return {
            "weapon": self.weapon,
            "amp": self.amp,
            "scope": self.scope,
            "sight_1": self.sight_1,
            "sight_2": self.sight_2,
            "damage_enh": self.damage_enh,
            "accuracy_enh": self.accuracy_enh,
            "economy_enh": self.economy_enh
        }

    @classmethod
    def load(cls, raw):
        """
        Load a raw dictionary representation of the object and return an instance of the class.

        :param raw: A dictionary containing the raw data.
        :type raw: dict
        :return: An instance of the class.
        :rtype: cls
        """
        return cls(**raw)


CustomWeapon = namedtuple("CustomWeapon", ["weapon", "decay", "ammo_burn"])


class HuntingTrip(object):

    def __init__(self, time_start: datetime, cost_per_shot: Decimal):
        self.time_start = time_start
        self.time_end = None

        self.notes = ""

        self.cost_per_shot: Decimal = cost_per_shot

        self.tt_return = 0
        self.globals = 0
        self.hofs = 0
        self.total_cost = 0
        self.cached_total_return_mu = Decimal("0.0")

        self.last_loot_instance = None
        self.loot_instances = 0
        self.extra_spend = Decimal(0.0)

        # Tracking multipliers
        self.loot_instance_cost = Decimal(0)
        self.loot_instance_value = Decimal(0)
        self.multipliers = ([], [])
        self.return_over_time = []

        self.looted_items = defaultdict(lambda: {"c": 0, "v": Decimal()})

        self.adjusted_cost = Decimal(0)

        # Enhancers
        self.enhancer_breaks = defaultdict(int)

        # Skillgains
        self.skillgains = defaultdict(int)
        self.skillprocs = defaultdict(int)

        # Combat Stats
        self.total_attacks = 0
        self.total_damage = 0
        self.total_crits = 0
        self.total_misses = 0

    def serialize_run(self):
        """
        Serializes the run into a dictionary format.

        Returns:
            dict: The serialized run data.
        """
        return {
            "start": dt_to_ts(self.time_start),
            "end": dt_to_ts(self.time_end) if self.time_end else None,
            "notes": self.notes,
            "config": {
                "cps": str(self.cost_per_shot)
            },
            "summary": {
                "tt_return": str(self.tt_return),
                "total_cost": str(self.total_cost),
                "extra_spend": str(self.extra_spend),
                "globals": self.globals,
                "hofs": self.hofs,
                "loots": self.loot_instances,
                "adj_cost": str(self.adjusted_cost),
                "cached_mu_return": str(self.total_return_mu)
            },
            "loot": {k: {"c": str(v["c"]), "v": str(v["v"])} for k, v in self.looted_items.items()},
            "skills": dict(self.skillgains),
            "skillprocs": dict(self.skillprocs),
            "enhancers": dict(self.enhancer_breaks),
            "combat": {
                "attacks": self.total_attacks,
                "dmg": self.total_damage,
                "crits": self.total_crits,
                "misses": self.total_misses
            },
            "graphs": {
                "returns": self.return_over_time,
                "multis": list(self.multipliers)
            }
        }

    @classmethod
    def from_seralized(cls, seralized, include_loot=False):
        """
        Create an instance of the class from a serialized dictionary.

        Parameters:
        - cls: The class object.
        - seralized: The serialized dictionary containing the data for the instance.
        - include_loot: Optional boolean indicating whether to include loot data.

        Returns:
        - inst: The instance of the class created from the serialized dictionary.
        """
        inst = cls(ts_to_dt(seralized["start"]), Decimal(seralized["config"]["cps"]))
        inst.notes = seralized.get("notes", "")

        if seralized["end"]:
            inst.time_end = ts_to_dt(seralized["end"])

        # loot
        inst.tt_return = Decimal(seralized["summary"]["tt_return"])
        inst.extra_spend = Decimal(seralized["summary"].get("extra_spend", "0.0"))
        inst.cached_total_return_mu = Decimal(seralized["summary"].get("cached_mu_return", "0.0"))
        inst.globals = seralized["summary"]["globals"]
        inst.hofs = seralized["summary"]["hofs"]
        inst.loot_instances = seralized["summary"]["loots"]
        inst.adjusted_cost = Decimal(seralized["summary"]["adj_cost"])
        if "total_cost" not in seralized["summary"]:
            # Fix for case where total_cost wont be present in serialized runs
            total_cost = Decimal(seralized["config"]["cps"]) * int(seralized["combat"]["attacks"])
            inst.total_cost = total_cost
        else:
            inst.total_cost = Decimal(seralized["summary"].get("total_cost", "0.0"))

        # combat
        inst.total_attacks = seralized["combat"]["attacks"]
        inst.total_damage = seralized["combat"]["dmg"]
        inst.total_crits = seralized["combat"]["crits"]
        inst.total_misses = seralized["combat"]["misses"]

        # graphs
        if include_loot:
            inst.return_over_time = seralized["graphs"]["returns"]
            inst.multipliers = seralized["graphs"]["multis"]

        for k, v in seralized["enhancers"].items():
            inst.enhancer_breaks[k] = v

        for k, v in seralized["skills"].items():
            inst.skillgains[k] = v

        if include_loot:
            for k, v in seralized["loot"].items():
                inst.looted_items[k] = {"c": int(v["c"]), "v": Decimal(v["v"])}

        return inst

    @classmethod
    def load_from_filename(cls, fn, include_loot=False):
        """
        Load an instance of the class from a file with the specified filename.

        Args:
            fn (str): The filename of the file to load from.
            include_loot (bool, optional): Whether to include the loot in the loaded instance. Defaults to False.

        Returns:
            The loaded instance of the class.
        """
        with open(format_filename(fn), 'r') as f:
            content = f.read()
        return cls.from_seralized(json.loads(content), include_loot=include_loot)

    @property
    def filename(self):
        """
        Return the filename for the LootNannyLog JSON file.

        Returns:
            str: The filename for the LootNannyLog JSON file.
        """
        return format_filename(f"LootNannyLog_{dt_to_ts(self.time_start)}.json")

    def save_to_disk(self):
        """
        Saves data to disk by opening a file with the given filename and writing the serialized run data in JSON format.

        Parameters:
            None

        Returns:
            None
        """
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self.serialize_run()))

    @property
    def duration(self):
        """
        Calculates the duration of an event.

        :return: The duration of the event in hours:minutes:seconds format.
        """
        d = self.time_end - self.time_start if self.time_end else datetime.now() - self.time_start
        return "{}:{}:{}".format(d.hours, d.seconds // 60, d.seconds % 60)

    def add_skillgain_row(self, row: SkillRow):
        """
        Adds a skill gain row to the skillgains and skillprocs dictionaries.
        
        Args:
            row (SkillRow): The skill row to be added.
        
        Returns:
            None
        """
        self.skillgains[row.skill] += row.amount
        self.skillprocs[row.skill] += 1

    def add_enhancer_break_row(self, row: EnhancerBreakages):
        """
        Increment the count of the given EnhancerBreakages type in the enhancer_breaks dictionary.

        Parameters:
            row (EnhancerBreakages): An instance of the EnhancerBreakages class representing the row to be added.

        Returns:
            None
        """
        self.enhancer_breaks[row.type] += 1

    @property
    def total_enhancer_breaks(self):
        """
        Returns the total number of enhancer breaks.

        :return: The total number of enhancer breaks.
        :rtype: int
        """
        return sum(self.enhancer_breaks.values())

    def add_global_row(self, row: GlobalInstance):
        """
        Adds a global row to the instance.

        Parameters:
            row (GlobalInstance): The global row to be added.

        Returns:
            None
        """
        if row.hof:
            self.hofs += 1
            return
        self.globals += 1

    def add_combat_chat_row(self, row: CombatRow):
        """
        Increment the statistics for combat chat rows.

        Args:
            row (CombatRow): The combat row to be added.

        Returns:
            None
        """
        self.total_attacks += 1
        self.total_damage += row.amount
        if row.critical:
            self.total_crits += 1
        if row.miss:
            self.total_misses += 1
        self.loot_instance_cost += self.cost_per_shot
        self.total_cost += self.cost_per_shot

    def add_loot_instance_chat_row(self, row: LootInstance):
        """
        Add a loot instance chat row to the loot tracking system.

        Args:
            row (LootInstance): The loot instance to be added.
        
        Returns:
            None

        Raises:
            None
        """
        ts = time.mktime(row.time.timetuple()) // 2

        # We dont want to consider sharp conversion as a loot event
        if row.name == "Universal Ammo":
            return

        if self.last_loot_instance != ts:
            # If looks like an enhancer break
            if row.name == "Vibrant Sweat":
                # Dont count sweat as a loot instance either
                pass
            elif row.name == "Shrapnel" and row.amount in {8000, 4000, 6000}:
                pass  # But we still add the shrapnel back to the total items looted
            else:
                self.last_loot_instance = ts
                self.loot_instances += 1

                if self.loot_instance_value and self.loot_instance_cost:
                    self.multipliers[0].append(float(self.loot_instance_cost))
                    self.multipliers[1].append(float(self.loot_instance_value))

                    self.loot_instance_cost = Decimal(0)
                    self.loot_instance_value = Decimal(0)

                    self.return_over_time.append(float(self.tt_return / self.total_cost))

        self.tt_return += row.value

        self.looted_items[row.name]["v"] += row.value
        self.looted_items[row.name]["c"] += row.amount
        self.loot_instance_value += row.value

    @property
    def miss_chance(self):
        """
        Calculate the miss chance of the player based on the total number of attacks and misses.

        Returns:
            str: The miss chance as a percentage, formatted with two decimal places.
        """
        if self.total_attacks == 0:
            return "0.00%"
        return "%.2f" % (self.total_misses / float(self.total_attacks) * 100) + "%"

    @property
    def crit_chance(self):
        """
        Calculate the critical chance for the player.

        Returns:
            str: The critical chance as a percentage (e.g. "0.00%").
        """
        if self.total_attacks == 0:
            return "0.00%"
        return "%.2f" % (self.total_crits / float(self.total_attacks) * 100) + "%"

    @property
    def dpp(self):
        """
        Calculates the damage per cost ratio.

        Returns:
            Decimal: The damage per cost ratio.
        """
        if self.total_cost > Decimal(0):
            return Decimal(self.total_damage) / (Decimal(self.total_cost + self.extra_spend) * 100)
        return Decimal(0.0)

    def get_skill_table_data(self):
        d = {"Skill": [], "Value": [], "Procs":[], "Proc %":[]}
        for k, v in sorted(self.skillgains.items(), key=lambda t: t[1], reverse=True):
            d["Skill"].append(k)
            d["Value"].append("%.4f" % v)
        
        # Get total procs during hunt
        tp = sum(i[1] for i in sorted(self.skillprocs.items(), key=lambda t: t[1], reverse=True))
        for k, v in sorted(self.skillprocs.items(), key=lambda t: t[1], reverse=True):
            d["Procs"].append(v)
            d["Proc %"].append("{:.00%}".format(v/tp)) if tp != 0 else d["Proc %"].append("{:.00%}".format(0))
        return d

    def get_total_skill_gain(self):
        return sum(self.skillgains.values())

    def get_enhancer_table_data(self):
        d = {"Enhancer": [], "Breaks": []}
        for k, v in sorted(self.enhancer_breaks.items(), key=lambda t: t[1], reverse=True):
            d["Enhancer"].append(k)
            d["Breaks"].append(str(v))
        return d

    def get_item_loot_table_data(self):
        r = {"Item": [], "Value": [], "Count": [], "Markup": [], "Total Value": []}
        for k, v in sorted(self.looted_items.items(), key=lambda t: t[1]["v"], reverse=True):
            r["Item"].append(k)
            r["Value"].append(str(v["v"]))
            r["Count"].append(str(v["c"]))
            mu = MarkupSingleton.get_markup_for_item(k)
            if mu.is_absolute:
                r["Markup"].append("+{:.3f}".format(mu.value))
                r["Total Value"].append("{:.4f}".format(v["v"] + (v["c"] * mu.value)))
            else:
                r["Markup"].append("{:.3f}%".format(mu.value * 100))
                r["Total Value"].append("{:.4f}".format(v["v"] * mu.value))
        return r

    @property
    def total_return_mu(self):
        """
        Calculates the total return in markup units (mu) for the current instance.

        Returns:
            Decimal: The total return in markup units (mu) for the current instance.
        """
        total_return_mu = Decimal("0.0")
        if len(self.looted_items) == 0:
            total_return_mu = self.cached_total_return_mu
        for k, v in self.looted_items.items():
            mu = MarkupSingleton.get_markup_for_item(k)
            if mu.is_absolute:
                total_return_mu += (v["v"] + (v["c"] * mu.value))
            else:
                total_return_mu += (v["v"] * mu.value)
        return total_return_mu

    @property
    def total_return_mu_perc(self):
        """
        Calculate the percentage of the total return on investment (ROI) in terms of monetary units (MU).

        Returns:
            float: The percentage of the total return on investment (ROI) in terms of monetary units (MU).
        """
        if self.total_cost + self.extra_spend:
            return self.total_return_mu / (self.total_cost + self.extra_spend) * 100
        else:
            return Decimal("0.0")


class CombatModule(BaseModule):

    def __init__(self, app):
        super().__init__()
        self.app = app

        # Core
        self.is_logging = False
        self.is_paused = False
        self.should_redraw_runs = True

        # Both of these are set by the parent app
        self.loot_table = None
        self.runs_table = None
        self.skill_table = None
        self.enhancer_table = None
        self.combat_fields = {}
        self.loot_fields = {}

        # Calculated Configuration
        self.ammo_burn = 0
        self.decay = 0

        # Runs
        self.active_run: HuntingTrip = None
        self.runs: List[HuntingTrip] = []

        # Graphs
        self.multiplier_graph = None
        self.return_graph = None

    def update_active_run_cost(self):
        """
        Update the cost per shot for the active run.

        This function calculates the cost per shot for the active run based on the ammo burn and decay values.
        If there is an active run, it calculates the cost using the formula:
        cost = Decimal(self.ammo_burn) / Decimal(10000) + self.decay

        Parameters:
            None

        Returns:
            None
        """
        if self.active_run:
            cost = Decimal(self.ammo_burn) / Decimal(10000) + self.decay
            self.active_run.cost_per_shot = cost

    def tick(self, lines: List[BaseChatRow]):
        """
        Processes a list of chat lines and updates the internal state of the application.

        Parameters:
            lines (List[BaseChatRow]): The list of chat lines to process.

        Returns:
            None
        """
        if self.is_logging and not self.is_paused:

            if self.active_run is None:
                self.create_new_run()

            for chat_instance in lines:
                if isinstance(chat_instance, CombatRow):
                    self.active_run.add_combat_chat_row(chat_instance)
                    self.should_redraw_runs = True
                elif isinstance(chat_instance, LootInstance):
                    self.active_run.add_loot_instance_chat_row(chat_instance)
                    self.should_redraw_runs = True
                elif isinstance(chat_instance, EnhancerBreakages):
                    self.active_run.add_enhancer_break_row(chat_instance)
                elif isinstance(chat_instance, SkillRow):
                    self.active_run.add_skillgain_row(chat_instance)
                elif isinstance(chat_instance, GlobalInstance):
                    if chat_instance.name.strip() == self.app.config.name.value.strip():
                        if self.app.config.screenshot_enabled.value:
                            t = threading.Thread(target=take_screenshot, args=(
                                self.app.config.screenshot_delay.value,
                                self.app.config.screenshot_directory.value,
                                chat_instance, ))
                            t.start()
                        self.active_run.add_global_row(chat_instance)

            if self.app.streamer_window:
                self.app.streamer_window.set_text_from_module(self)

        if self.runs and self.should_redraw_runs:
            self.update_tables()
            self.should_redraw_runs = False

    def update_tables(self):
        """
        Updates the various tables used in the game.

        This function calls multiple update functions to update the loot table,
        combat table, skill table, enhancer table, and graphs.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        self.update_loot_table()
        self.update_combat_table()
        self.update_skill_table()
        self.update_enhancer_table()
        self.update_graphs()

    def update_combat_table(self):
        """
        {
            "attacks": shots_text,
            "damage": damage_text,
            "crits": critical_rate,
            "misses": miss_rate,
            "dpp": dpp,
            "enhancer_table": table
        }
        :return:
        """
        if not self.active_run:
            return
        self.combat_fields["attacks"].setText(str(self.active_run.total_attacks))
        self.combat_fields["damage"].setText("%.2f" % self.active_run.total_damage)
        self.combat_fields["crits"].setText(str(self.active_run.crit_chance))
        self.combat_fields["misses"].setText(str(self.active_run.miss_chance))
        self.combat_fields["dpp"].setText("%.4f" % self.active_run.dpp)

    def update_loot_table(self):
        """
        {
            "looted_text": looted_text,
            "total_cost_text": total_cost_text,
            "total_return_text": total_return_text,
            "return_perc_text": return_perc_text,
            "globals": globals,
            "hofs": hofs
        }
        :return:
        """
        if not self.active_run:
            return
        self.loot_table.clear()
        self.loot_fields["looted_text"].setText(str(self.active_run.loot_instances))
        self.loot_fields["total_cost_text"].setText("%.2f" % self.active_run.total_cost)
        self.loot_fields["total_return_text"].setText("%.2f" % self.active_run.tt_return)
        if self.active_run.total_cost:
            self.loot_fields["return_perc_text"].setText("%.2f" % (self.active_run.tt_return / self.active_run.total_cost * 100))
        self.loot_fields["globals"].setText(str(self.active_run.globals))
        self.loot_fields["hofs"].setText(str(self.active_run.hofs))

        self.loot_table.setData(self.active_run.get_item_loot_table_data())
        self.loot_table.resizeRowsToContents()
        self.update_runs_table()

    def update_runs_table(self):
        """
        Update the runs table with the latest data.

        This function retrieves the runs data using the `get_runs_data()` method and
        sets it to the `runs_table` using the `setData()` method.

        Parameters:
            self (object): The instance of the current class.

        Returns:
            None
        """
        self.runs_table.setData(self.get_runs_data())

    def update_skill_table(self):
        """
        Updates the skill table with the data from the active run.

        Parameters:
            self (object): The instance of the class.
        
        Returns:
            None
        """
        if not self.active_run:
            return
        self.skill_table.clear()
        self.skill_table.setData(self.active_run.get_skill_table_data())
        self.app.total_skills_text.setText(f"{self.active_run.get_total_skill_gain():.4f}")

    def update_enhancer_table(self):
        """
        Updates the enhancer table with the data from the active run.

        This function clears the enhancer table and then sets the data using the
        `get_enhancer_table_data` method of the active run object.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        if not self.active_run:
            return
        self.enhancer_table.clear()
        self.enhancer_table.setData(self.active_run.get_enhancer_table_data())

    def update_graphs(self):
        """
        Update the graphs displayed on the GUI.

        This function is responsible for updating the return graph and the multiplier graph
        with the data from the active run. If there is no active run, the graphs will not be
        updated.

        Parameters:
        - None

        Returns:
        - None
        """
        if not self.active_run:
            return
        self.return_graph.clear()
        self.return_graph.plot(list(map(lambda x: float(x * 100), self.active_run.return_over_time)))
        self.multiplier_graph.clear()
        self.multiplier_graph.plot(*self.active_run.multipliers, pen=None, symbol="o")

    def get_runs_data(self):
        """
        Retrieves data from the runs and organizes it into a dictionary.

        Returns:
            dict: A dictionary containing the following keys:
                - "Notes": A list of notes for each run.
                - "Start": A list of start times for each run.
                - "End": A list of end times for each run.
                - "Spend": A list of total costs for each run.
                - "Enhancers": A list of total enhancer breaks for each run.
                - "Extra Spend": A list of extra spend amounts for each run.
                - "Return": A list of returns for each run.
                - "%": A list of return percentages for each run.
                - "mu%": A list of total return mu percentages for each run.
        """
        d = {"Notes": [], "Start": [], "End": [], "Spend": [],
             "Enhancers": [], "Extra Spend": [], "Return": [], "%": [], "mu%": []}
        for run in self.runs[::-1]:
            run: HuntingTrip
            d["Notes"].append(run.notes)
            d["Start"].append(run.time_start.strftime("%Y-%m-%d %H:%M:%S"))
            d["End"].append(run.time_end.strftime("%Y-%m-%d %H:%M:%S") if run.time_end else "")
            d["Spend"].append("%.2f" % run.total_cost)
            d["Enhancers"].append(str(run.total_enhancer_breaks))
            d["Extra Spend"].append(str(run.extra_spend))
            d["Return"].append(run.tt_return)
            if run.total_cost + run.extra_spend:
                d["%"].append("%.2f" % (run.tt_return / (run.total_cost + run.extra_spend) * 100) + "%")
                d["mu%"].append("%.2f" % (run.total_return_mu_perc) + "%")
            else:
                d["%"].append("%")
                d["mu%"].append("%")
        return d

    def create_new_run(self):
        """
        Create a new run for the hunting trip.

        This function initializes a new `HuntingTrip` object and assigns it to the `active_run`
        attribute. The `HuntingTrip` object is created with the current date and time obtained
        from `datetime.now()`, and the calculated value of ammo burn divided by 10000 plus the
        decay value.

        Parameters:
            self (HuntingTrip): The instance of the `HuntingTrip` class.

        Returns:
            None
        """
        self.active_run = HuntingTrip(datetime.now(), Decimal(self.ammo_burn) / Decimal(10000) + self.decay)
        self.runs.append(self.active_run)

    def save_active_run(self, force=False):
        """
        Save the active run to disk.

        Parameters:
            force (bool): Whether to save the active run even if it is None. Defaults to False.

        Returns:
            None
        """
        if not self.active_run:
            if not force:
                return
            if self.runs:
                self.runs[-1].save_to_disk()
        else:
            self.active_run.save_to_disk()

    def load_runs(self):
        """
        Load runs from the specified directory and populate the `runs` list with the loaded data.

        This function performs the following steps:
        1. If the `RUNS_FILE` exists, migrate the runs to the new system and remove the old file.
        2. If the `RUNS_DIRECTORY` exists, load each file in the directory and add the valid ones to the `run_files` list.
        3. For each file in the `run_files` list, load the run data using the `HuntingTrip.load_from_filename()` method and append it to the `runs` list.
        4. If the `runs` list is not empty, set the `active_run` to the last run if it is still ongoing, otherwise update the runs table.

        This function does not take any parameters and does not return any values.
        """
        if os.path.exists(RUNS_FILE):
            # Old system of saving runs, need to migrate
            migrate_runs()

            os.remove(RUNS_FILE)

            time.sleep(5)

        if not os.path.exists(RUNS_DIRECTORY):
            return

        run_files = []

        for fn in os.listdir(RUNS_DIRECTORY):
            if fn.startswith("LootNannyLog_"):
                try:
                    with open(format_filename(fn), 'r') as f:
                        json.loads(f.read())
                    run_files.append(fn)
                except:
                    os.remove(format_filename(fn))

        for i, run_fn in enumerate(run_files, 1):
            run = HuntingTrip.load_from_filename(run_fn, include_loot=(i == len(run_files)))
            self.runs.append(run)

        if self.runs:
            if self.runs[-1].time_end is None:
                self.active_run = self.runs[-1]
            else:
                self.update_runs_table()


def migrate_runs():
    """
    Migrates the runs data from a file to the disk.

    This function reads the runs data from the specified file and migrates it to the disk. The runs data is stored in a JSON format. The function first opens the file in read mode and attempts to read the contents. If an error occurs during the reading process, it prints a message indicating that a corrupted runs file has been detected, and it prints the raw data that was read. After reading the data, it attempts to parse the JSON and store it in the `data` variable. If the parsing fails, an empty dictionary is assigned to `data`.

    After reading and parsing the data, the function iterates over each `run_data` in `data`. For each `run_data`, it deserializes the data using the `HuntingTrip.from_serialized` method and assigns the result to the `run` variable. Finally, it saves the `run` to the disk using the `run.save_to_disk()` method.

    Parameters:
    - None

    Returns:
    - None
    """
    with open(RUNS_FILE, 'r') as f:
        try:
            raw_data = f.read()
            data = json.loads(raw_data)
        except:
            print("Corrpted Runs File Detected")
            print(raw_data)
            data = {}

    for run_data in data:
        run = HuntingTrip.from_seralized(run_data)
        run.save_to_disk()
