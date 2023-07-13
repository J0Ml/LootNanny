from enum import Enum
from twitchio.ext import commands
from decimal import Decimal
import time

from modules.combat import CombatModule


class Commands(str, Enum):
    INFO = "info"
    COMMANDS = "commands"
    TOP_LOOTS = "toploots"
    ALL_RETURNS = "allreturns"


def format_info():
    """
    A function that returns the formatted information about the LootNanny program.

    Returns:
        str: The formatted information about the LootNanny program.
    """
    return """
    LootNanny is a LootTracker program created by Nanashana Nana Itsanai
    Download it at: https://github.com/euloggeradmin/LootNanny/releases
    """


def format_commands(commands):
    """
    Formats the list of commands into a string.

    Args:
        commands (list): A list of Command objects representing the available commands.

    Returns:
        str: A string containing the available commands, separated by commas.
    """
    return f"""
    Available commands: {', '.join([str(c.value) for c in commands])}
    """


def format_top_loots(combat_module: CombatModule):
    """
    Formats the top loots from a given CombatModule.

    Parameters:
    - combat_module (CombatModule): The CombatModule containing the loots.

    Returns:
    - str: A formatted string representing the top 5 loots, separated by ' --- '.
    """
    all_mulitis = []
    for run in combat_module.runs:
        for multi in run.multipliers[1]:
            all_mulitis.append(multi)
    top_5 = " --- ".join(map(lambda v: "%.2f" % v + " PED", sorted(all_mulitis, reverse=True)[:5]))
    return f"""
    Top Loots:                 
    {top_5}
    """


def format_all_returns(combat_module: CombatModule):
    """
    Calculates the total spend, total returns, and total percentage for a given combat module.

    Args:
        combat_module (CombatModule): The combat module for which to calculate the totals.

    Returns:
        str: A formatted string containing the total spend, total returns, and total percentage.

    """ 
    all_spend = Decimal(0)
    all_return = Decimal(0)

    for run in combat_module.runs:
        all_return += run.tt_return
        all_spend += run.total_cost

    perc = all_return / all_spend * Decimal(100.0)

    return f"""
    Total Spend: {all_spend:.2f} PED
    Total Returns: {all_return:.2f} PED
    Total %: {perc:.2f}%
    """


class StopException(Exception):
    pass


class TwitchIntegration(commands.Bot):

    def __init__(self, app, username="", token="", channel="", command_prefix=""):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        self.app = app
        self.username = username
        self.command_prefix = command_prefix
        super().__init__(token=token, prefix=command_prefix, initial_channels=[channel])
        self.running = True
        self.exited = False

    def run(self):
        """
        A blocking function that starts the asyncio event loop,
        connects to the twitch IRC server, and cleans up when done.
        """
        try:
            self.loop.create_task(self.connect())
            self.loop.run_forever()
        except StopException:
            pass
        finally:
            self.loop.stop()
            time.sleep(2)
            self.loop.close()
            self.exited = True

    async def event_ready(self):
        """
        A function that is called when the event "ready" is triggered.

        This function is responsible for handling the event when the bot is logged in and ready to chat and use commands.

        Parameters:
            self (class): An instance of the class.

        Returns:
            None
        """
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.username}')

    @commands.command()
    async def lootnanny(self, ctx: commands.Context):
        """
        A command that sends a message back to the channel.

        Parameters:
        - ctx (commands.Context): The context of the command.

        Returns:
        - None
        """
        # Here we have a command hello, we can invoke our command with our prefix and command name
        # e.g ?hello
        # We can also give our commands aliases (different names) to invoke with.

        # Send a hello back!
        # Sending a reply back to the channel is easy... Below is an example.
        extra_command = ctx.message.content.lstrip(self.command_prefix + "lootnanny").strip()

        try:
            cmd = Commands(extra_command)
            if cmd not in self.app.twitch.commands_enabled:
                cmd = Commands.COMMANDS
        except:
            cmd = Commands.COMMANDS

        if cmd == Commands.INFO:
            msg = format_info()
        elif cmd == Commands.COMMANDS:
            msg = format_commands(self.app.twitch.commands_enabled)
        elif cmd == Commands.TOP_LOOTS:
            msg = format_top_loots(self.app.combat_module)
        elif cmd == Commands.ALL_RETURNS:
            msg = format_all_returns(self.app.combat_module)

        await ctx.send(msg)

    def start(self):
        """
        Starts the execution of the program by calling the `run` method.
        """
        self.run()
