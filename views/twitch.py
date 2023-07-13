import os
import json
import webbrowser
from threading import Thread
import time

from PyQt5.QtWidgets import QFileDialog, QTextEdit, QHBoxLayout, QFormLayout, QHeaderView, QTabWidget, QCheckBox, QGridLayout, QComboBox, QLineEdit, QLabel, QApplication, QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem
from modules.twitch import Commands, TwitchIntegration


CMD_NAMES = {
    Commands.INFO: "Information (info)",
    Commands.COMMANDS: "List Commands (commands)",
    Commands.TOP_LOOTS: "Top Loots (toploots)",
    Commands.ALL_RETURNS: "All Returns (allreturns)"
}


class TwitchTab(QWidget):

    def __init__(self, app: "LootNanny", config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app = app

        self.command_toggles = {}

        self.create_layout()

        # Bot
        self.twitch_bot = None
        self.twitch_bot_thread = None

        # Finalize Initialization
        self.validate_settings()

    def to_config(self):
        """
        Converts the current object into a dictionary representation of a configuration.
        
        Returns:
            dict: A dictionary representing the configuration with the following keys:
                - "token" (str): The OAuth token.
                - "username" (str): The username.
                - "channel" (str): The channel.
                - "prefix" (str): The command prefix.
                - "commands_enabled" (List[str]): A list of enabled command values.
        """
        return {
            "token": self.oauth_token,
            "username": self.username,
            "channel": self.channel,
            "prefix": self.command_prefix,
            "commands_enabled": list(map(lambda c: c.value, self.commands_enabled))
        }

    def create_layout(self):
        """
        Creates a layout for the widget.
        
        Returns:
            QVBoxLayout: The layout for the widget.
        """
        layout = QVBoxLayout()

        form_inputs = QFormLayout()
        layout.addLayout(form_inputs)

        # Chat Location
        self.oauth_token_text = QLineEdit(self.app.config.twitch_token.ui_value)
        self.oauth_token_text.editingFinished.connect(self.on_settings_changed)
        form_inputs.addRow("OAuth Token:", self.oauth_token_text)

        btn = QPushButton("Get New OAuth Token:")
        btn.released.connect(lambda: webbrowser.open("https://twitchapps.com/tmi"))
        form_inputs.addWidget(btn)

        self.username_text = QLineEdit(self.app.config.twitch_username.ui_value, enabled=False)
        self.username_text.editingFinished.connect(self.on_settings_changed)
        form_inputs.addRow("Bot Name:", self.username_text)

        self.channel_text = QLineEdit(self.app.config.twitch_channel.ui_value)
        self.channel_text.editingFinished.connect(self.on_settings_changed)
        form_inputs.addRow("Channel:", self.channel_text)

        self.command_prefix_text = QLineEdit(self.app.config.twitch_prefix.ui_value)
        self.command_prefix_text.editingFinished.connect(self.on_settings_changed)
        form_inputs.addRow("Command Prefix:", self.command_prefix_text)

        for i, cmd in enumerate(Commands):
            widget = QCheckBox(CMD_NAMES[cmd.value], self)
            widget.setChecked(cmd in self.app.config.twitch_commands_enabled.value)
            layout.addWidget(widget)
            widget.toggled.connect(self.on_commands_toggled)
            self.command_toggles[cmd] = widget

        layout.addStretch()

        self.start_btn = QPushButton("Start Twitch Bot:", enabled=False)
        self.start_btn.released.connect(self.start_twitch_bot)
        form_inputs.addWidget(self.start_btn)

        self.setLayout(layout)

    def start_twitch_bot(self):
        """
        Starts the Twitch bot and disables the start button.

        Parameters:
            None

        Returns:
            None
        """
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Restart App To Start Twitch Bot Again :( (Work in progress)")
        if self.twitch_bot is not None:
            # Kill old twitch bot
            return  # TODO: This is harder than I first intneded to do cleanly, maybe need a daemon process :(

        print("Starting twitch bot")
        self.twitch_bot = TwitchIntegration(
            self.app,
            username=self.username,
            token=self.oauth_token,
            channel=self.channel,
            command_prefix=self.command_prefix
        )
        self.twitch_bot_thread = Thread(target=self.twitch_bot.start, daemon=True)
        self.twitch_bot_thread.start()

    def on_settings_changed(self):
        """
        Updates the Twitch settings based on the values entered in the UI.

        This function retrieves the values entered in the UI for the Twitch token, username, channel, and command prefix. 
        It then updates the corresponding attributes in the application's configuration.

        Parameters:
            self (object): The instance of the class.
        
        Returns:
            None
        """
        self.app.config.twitch_token = self.oauth_token_text.text()
        self.app.config.twitch_username = self.username_text.text()
        self.app.config.twitch_channel = self.channel_text.text()
        self.app.config.twitch_prefix = self.command_prefix_text.text()

        self.validate_settings()
        self.app.save_config()

    def validate_settings(self):
        """
        Validates the settings of the application.

        This function checks if all the required settings for the application are
        provided. The required settings include the Twitch token, Twitch username,
        Twitch channel, and Twitch prefix. If all the required settings are provided,
        the 'start_btn' is enabled. Otherwise, the 'start_btn' is disabled.

        Parameters:
            self (object): The current instance of the class.

        Returns:
            None
        """
        if all([
            self.app.config.twitch_token.value,
            self.app.config.twitch_username.value,
            self.app.config.twitch_channel.value,
            self.app.config.twitch_prefix.value
        ]):
            self.start_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(False)

    def on_commands_toggled(self):
        """
        Toggles the commands based on the state of the checkboxes.

        This function iterates through the dictionary `self.command_toggles` which contains the checkboxes for each command. For each command, it checks if the corresponding checkbox is checked. If it is, the command is added to the set `self.app.config.twitch_commands_enabled.value`. If the checkbox is not checked, the command is removed from the set. After iterating through all the commands, the function saves the updated configuration.

        Parameters:
            None

        Returns:
            None
        """
        for command, checkbox in self.command_toggles.items():
            checkbox: QComboBox
            if checkbox.isChecked():
                self.app.config.twitch_commands_enabled.value.add(command)
            else:
                self.app.config.twitch_commands_enabled.value.discard(command)
        self.app.save_config()
