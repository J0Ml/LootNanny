import tailer
import enum
from datetime import datetime
from collections import namedtuple
import re
import time
import win_unicode_console
import threading

from decimal import Decimal
win_unicode_console.enable()

# Enum for different types of chat messages
class ChatType(str, enum.Enum):
    HEAL = "heal"
    COMBAT = "combat"
    SKILL = "skill"
    DEATH = "death"
    EVADE = "evade"
    DAMAGE = "damage"
    DEFLECT = "deflect"
    DODGE = "dodge"
    ENHANCER = "enhancer"
    LOOT = "loot"
    GLOBAL = "global"

# Base class for chat rows
class BaseChatRow(object):
    def __init__(self, *args, **kwargs):
        self.time = None

# Chat row for healing messages
class HealRow(BaseChatRow):
    def __init__(self, amount):
        super().__init__()
        self.amount = float(amount)

# Chat row for combat messages
class CombatRow(BaseChatRow):
    def __init__(self, amount=0.0, critical=False, miss=False):
        super().__init__()
        self.amount = float(amount) if amount else 0.0
        self.critical = critical
        self.miss = miss

# Chat row for skill gain messages
class SkillRow(BaseChatRow):
    def __init__(self, amount, skill):
        super().__init__()
        try:
            self.amount = float(amount)
            self.skill = skill
        except ValueError:
            # Attributes have their values swapped around in the chat message
            self.amount = float(skill)
            self.skill = amount

# Chat row for enhancer breakage messages
class EnhancerBreakages(BaseChatRow):
    def __init__(self, type):
        super().__init__()
        self.type = type

# Chat row for loot messages
class LootInstance(BaseChatRow):
    CUSTOM_VALUES = {
        "Shrapnel": Decimal("0.0001")
    }

    def __init__(self, name, amount, value):
        super().__init__()
        self.name = name
        self.amount = int(amount)

        if name in self.CUSTOM_VALUES:
            self.value = Decimal(amount) * self.CUSTOM_VALUES[name]
        else:
            self.value = Decimal(value)

# Chat row for global messages
class GlobalInstance(BaseChatRow):
    def __init__(self, name, creature, value, location=None, hof=False):
        super().__init__()
        self.name = name
        self.creature = creature
        self.value = value
        self.hof = hof
        self.location = location

# Regular expression pattern for parsing log lines
LOG_LINE_REGEX = re.compile(
    r"([\d\-]+ [\d:]+) \[(\w+)\] \[(.*)\] (.*)"
)

# Named tuple for storing parsed log lines
LogLine = namedtuple("LogLine", ["time", "channel", "speaker", "msg"])

# Function to parse a raw string log line into a LogLine named tuple
def parse_log_line(line: str) -> LogLine:
    """
    Parses a raw string log line and returns an exploded LogLine for easier manipulation
    :param line: The line to process
    :return: LogLine
    """
    matched = LOG_LINE_REGEX.match(line)
    if not matched:
        return LogLine("", "", "", "")
    return LogLine(*matched.groups())

# Regular expressions and corresponding chat types, classes, and kwargs for parsing different chat messages
REGEXES = {
    re.compile("Critical hit - Additional damage! You inflicted (\d+\.\d+) points of damage"): (ChatType.DAMAGE, CombatRow, {"critical": True}),
    re.compile("You inflicted (\d+\.\d+) points of damage"): (ChatType.DAMAGE, CombatRow, {}),
    re.compile("You healed yourself (\d+\.\d+) points"): (ChatType.HEAL, HealRow, {}),
    re.compile("Damage deflected!"): (ChatType.DEFLECT, BaseChatRow, {}),
    re.compile("You Evaded the attack"): (ChatType.EVADE, BaseChatRow, {}),
    re.compile("You missed"): (ChatType.DODGE, CombatRow, {"miss": True}),
    re.compile("The target Dodged your attack"): (ChatType.DODGE, CombatRow, {"miss": True}),
    re.compile("The target Evaded your attack"): (ChatType.DODGE, CombatRow, {"miss": True}),
    re.compile("The target Jammed your attack"): (ChatType.DODGE, CombatRow, {"miss": True}),
    re.compile("You took (\d+\.\d+) points of damage"): (ChatType.DAMAGE, BaseChatRow, {}),
    re.compile("You have gained (\d+\.\d+) experience in your ([a-zA-Z ]+) skill"): (ChatType.SKILL, SkillRow, {}),
    re.compile("You have gained (\d+\.\d+) ([a-zA-Z ]+)"): (ChatType.SKILL, SkillRow, {}),
    re.compile("Your ([a-zA-Z ]+) has improved by (\d+\.\d+)"): (ChatType.SKILL, SkillRow, {}),
    re.compile("Your enhancer ([a-zA-Z0-9 ]+) on your .* broke."): (ChatType.ENHANCER, EnhancerBreakages, {}),
    re.compile(r"You received (.*) x \((\d+)\) Value: (\d+\.\d+) PED"): (ChatType.LOOT, LootInstance, {})
}

# Regular expressions and corresponding chat types, classes, and kwargs for parsing global messages
GLOBAL_REGEXES = {
    re.compile(r"([\w\s\'\(\)]+) killed a creature \(([\w\s\(\),]+)\) with a value of (\d+) PED! A record has been added to the Hall of Fame!"): (ChatType.GLOBAL, GlobalInstance, {"hof": True}),
    re.compile(r"([\w\s\'\(\)]+) killed a creature \(([\w\s\(\),]+)\) with a value of (\d+) PED!"): (ChatType.GLOBAL, GlobalInstance, {}),
    re.compile(r"([\w\s\'\(\)]+) constructed an item \(([\w\s\(\),]+)\) worth (\d+) PED! A record has been added to the Hall of Fame!"): (ChatType.GLOBAL, GlobalInstance, {"hof": True}),
    re.compile(r"([\w\s\'\(\)]+) constructed an item \(([\w\s\(\),]+)\) worth (\d+) PED!"): (ChatType.GLOBAL, GlobalInstance, {}),
    re.compile(r"([\w\s\'\(\)]+) found a deposit \(([\w\s\(\)]+)\) with a value of (\d+) PED! A record has been added to the Hall of Fame!"): (ChatType.GLOBAL, GlobalInstance, {"hof": True}),
    re.compile(r"([\w\s\'\(\)]+) found a deposit \(([\w\s\(\)]+)\) with a value of (\d+) PED!"): (ChatType.GLOBAL, GlobalInstance, {}),
    re.compile(r"([\w\s\'\(\)]+) killed a creature \(([\w\s\(\),]+)\) with a value of (\d+) PED at ([\s\w\W]+)!"): (ChatType.GLOBAL, GlobalInstance, {}),
}

# Class for reading chat lines from a log file
class ChatReader(object):
    def __init__(self, app):
        self.app = app
        self.lines = []
        self.reader = None

    def delay_start_reader(self):
        """
        Starts a reader thread to tail a log file.

        This function checks if a reader thread is already running. If a reader thread is already running, it returns without doing anything.

        If a reader thread is not running, it checks if the log file location is set in the application configuration. If the log file location is not set, it returns without doing anything.

        If the log file location is set, it opens the log file for reading and starts tailing it using the `tailer` library. The file is opened with the "utf_8_sig" encoding.

        After opening the file, it starts a new reader thread by creating a `threading.Thread` object. The `target` of the thread is set to the `readlines` method of the current object. The `daemon` flag is set to True to allow the thread to be terminated when the main thread exits. Finally, the thread is started.

        This function does not have any parameters.

        This function does not return anything.
        """
        if self.reader:
            return

        if not self.app.config.location.value:
            return

        # Open the log file for reading and start tailing it
        self.fd = tailer.follow(open(self.app.config.location.value, "r", encoding="utf_8_sig"), delay=0.01)
        self.reader = threading.Thread(target=self.readlines, daemon=True)
        self.reader.start()

    def readlines(self):
        """
        Reads lines from a file and parses them into chat instances.
        
        This method reads lines from the file object specified by `self.fd` and parses each line
        using the `parse_log_line` function. It then checks the channel of each parsed log line
        and processes it accordingly.
        
        Parameters:
            None
        
        Returns:
            None
        """
        try:
            for line in self.fd:
                log_line = parse_log_line(line)
                if log_line.channel == "System":
                    matched = False
                    for rx in REGEXES:
                        match = rx.search(log_line.msg)
                        if match:
                            chat_type, chat_cls, kwargs = REGEXES[rx]
                            chat_instance: BaseChatRow = chat_cls(*match.groups(), **kwargs)
                            chat_instance.time = datetime.strptime(log_line.time, "%Y-%m-%d %H:%M:%S")
                            self.lines.append(chat_instance)
                            matched = True
                            break
                    if not matched:
                        print([log_line.msg])
                elif log_line.channel == "Globals":
                    matched = False
                    for rx in GLOBAL_REGEXES:
                        match = rx.search(log_line.msg)
                        if match:
                            chat_type, chat_cls, kwargs = GLOBAL_REGEXES[rx]
                            chat_instance: GlobalInstance = chat_cls(*match.groups(), **kwargs)
                            chat_instance.time = datetime.strptime(log_line.time, "%Y-%m-%d %H:%M:%S")
                            self.lines.append(chat_instance)
                            matched = True
                            break
        except UnicodeDecodeError:
            pass

    def getline(self):
        """
        Get a line from the lines list if it is not empty.

        Returns:
            str or None: The first line from the lines list if it is not empty, otherwise None.
        """
        if len(self.lines):
            return self.lines.pop(0)
        return None

