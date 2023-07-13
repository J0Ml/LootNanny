from decimal import Decimal
import os
import json

from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QFileDialog, QTextEdit, QFormLayout, QHBoxLayout, QHeaderView, QTabWidget, QCheckBox, QGridLayout, QComboBox, QLineEdit, QLabel, QApplication, QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem

from data.weapons import ALL_WEAPONS
from data.sights_and_scopes import SIGHTS, SCOPES
from data.attachments import ALL_ATTACHMENTS
from modules.combat import Loadout, CustomWeapon
from utils.tables import WeaponTable


class ConfigTab(QWidget):

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app: "LootNanny" = app

        layout = QVBoxLayout()

        form_inputs = QFormLayout()
        # Add widgets to the layout

        self.refresh_custom_weapons()

        # Chat Location
        self.chat_location_text = QLineEdit(text=self.app.config.location.ui_value)
        form_inputs.addRow("Chat Location:", self.chat_location_text)
        self.chat_location_text.editingFinished.connect(self.onChatLocationChanged)

        btn = QPushButton("Find File")
        form_inputs.addWidget(btn)
        btn.clicked.connect(self.open_files)

        self.character_name = QLineEdit(text=self.app.config.name.ui_value)
        form_inputs.addRow("Character Name:", self.character_name)
        self.character_name.editingFinished.connect(self.onNameChanged)

        self.weapons = WeaponTable({"Name": [], "Amp": [], "Scope": [], "Sight 1": [],
                         "Sight 2": [], "Damage": [], "Accuracy": [], "Economy": []}, 25, 8)
        self.weapons.itemClicked.connect(self.weapon_table_selected)
        self.redraw_weapons()
        form_inputs.addRow("Weapons", self.weapons)

        # Other Windows
        self.select_loadout_btn = QPushButton("Select Loadout")
        self.select_loadout_btn.released.connect(self.select_loadout)
        self.select_loadout_btn.hide()
        form_inputs.addWidget(self.select_loadout_btn)

        self.delete_weapon_btn = QPushButton("Delete Loadout")
        self.delete_weapon_btn.released.connect(self.delete_loadout)
        self.delete_weapon_btn.hide()
        form_inputs.addWidget(self.delete_weapon_btn)

        self.add_weapon_btn = QPushButton("Add Weapon Loadout")
        self.add_weapon_btn.released.connect(self.add_new_weapon)
        form_inputs.addWidget(self.add_weapon_btn)

        self.create_weapon_btn = QPushButton("Create Weapon")
        self.create_weapon_btn.released.connect(self.create_weapon)
        form_inputs.addWidget(self.create_weapon_btn)

        self.active_loadout = QLineEdit(text="", enabled=False)
        form_inputs.addRow("Active Loadout:", self.active_loadout)

        # Calculated Configuration
        self.ammo_burn_text = QLineEdit(text="0", enabled=False)
        form_inputs.addRow("Ammo Burn:", self.ammo_burn_text)

        self.weapon_decay_text = QLineEdit(text="0.0", enabled=False)
        form_inputs.addRow("Tool Decay:", self.weapon_decay_text)

        # Screenshots
        self.screenshots_enabled = True
        self.screenshot_directory = "~/Documents/Globals/"
        self.screenshot_delay_ms = 500

        self.screenshots_checkbox = QCheckBox()
        self.screenshots_checkbox.setChecked(self.app.config.screenshot_enabled.value)
        self.screenshots_checkbox.toggled.connect(self.update_screenshot_fields)
        form_inputs.addRow("Take Screenshot On global/hof", self.screenshots_checkbox)

        self.screenshots_directory_text = QLineEdit(text=self.app.config.screenshot_directory.ui_value)
        form_inputs.addRow("Screenshot Directory:", self.screenshots_directory_text)
        self.screenshots_directory_text.textChanged.connect(self.update_screenshot_fields)

        self.screenshots_delay = QLineEdit(text=self.app.config.screenshot_delay.ui_value)
        form_inputs.addRow("Screenshot Delay (ms):", self.screenshots_delay)
        self.screenshots_delay.textChanged.connect(self.update_screenshot_fields)

        self.screenshot_threshold = QLineEdit(text=self.app.config.screenshot_threshold.ui_value)
        form_inputs.addRow("Screenshot Threshold (PED):", self.screenshot_threshold)
        self.screenshot_threshold.textChanged.connect(self.update_screenshot_fields)

        self.streamer_window_layout_text = QTextEdit()
        self.streamer_window_layout_text.setText(self.app.config.streamer_layout.ui_value)
        self.streamer_window_layout_text.textChanged.connect(self.set_new_streamer_layout)

        form_inputs.addRow("Streamer Window Layout:", self.streamer_window_layout_text)

        # Set Layout
        layout.addLayout(form_inputs)

        self.setLayout(layout)

        if self.app.config.selected_loadout.value:
            self.active_loadout.setText(self.app.config.selected_loadout.value.weapon)
            self.recalculateWeaponFields()

        if not os.path.exists(os.path.expanduser(self.screenshot_directory)):
            os.makedirs(os.path.expanduser(self.screenshot_directory))

    def refresh_custom_weapons(self):
        """
        Refreshes the list of custom weapons.

        This function iterates over each custom weapon in the `custom_weapons` configuration value and updates the `ALL_WEAPONS` dictionary accordingly. For each custom weapon, a new entry is added to the dictionary with the key "!CUSTOM - {weapon_name}". The value of the entry is a dictionary containing the type of the weapon (which is set to "custom"), the decay value (converted to a `Decimal` object), and the ammo burn value.

        Parameters:
            self (object): The current instance of the class.

        Returns:
            None
        """
        for custom_weapon in self.app.config.custom_weapons.value:
            custom_weapon = CustomWeapon(*custom_weapon)
            ALL_WEAPONS[f"!CUSTOM - {custom_weapon.weapon}"] = {
                "type": "custom",
                "decay": Decimal(custom_weapon.decay),
                "ammo": custom_weapon.ammo_burn
            }

    def weapon_table_selected(self):
        """
        This function is triggered when a weapon table item is selected.
        It retrieves the selected rows from the weapon table and performs the following actions:
        - If no rows are selected, it hides the delete weapon button, the select loadout button, 
          and sets the selected index to None.
        - If rows are selected, it shows the delete weapon button and the select loadout button,
          sets the selected index to the last selected row, and enables the delete weapon button.
        """
        indexes = self.weapons.selectionModel().selectedRows()
        if not indexes:
            self.delete_weapon_btn.hide()
            self.select_loadout_btn.hide()
            self.selected_index = None
            return

        self.delete_weapon_btn.show()
        self.select_loadout_btn.show()
        self.selected_index = indexes[-1].row()
        self.delete_weapon_btn.setEnabled(True)

    def select_loadout(self):
        """
        Selects a loadout from the available loadouts and updates the selected loadout in the app configuration.
        
        This function takes no parameters.
        
        There is no return value.
        """
        self.app.config.selected_loadout = self.app.config.loadouts.value[self.selected_index]
        self.active_loadout.setText(self.app.config.selected_loadout.value.weapon)
        self.recalculateWeaponFields()

    def delete_loadout(self):
        """
        Delete the selected loadout from the configuration.

        This function deletes the loadout at the selected index from the configuration. After deleting the loadout, 
        the configuration is saved to persist the changes. Finally, the weapons are redrawn to update the display.

        Parameters:
            self (object): The instance of the class.
        
        Returns:
            None
        """
        del self.app.config.loadouts.value[self.selected_index]
        self.app.config.save()
        self.redraw_weapons()

    def loadout_to_data(self):
        """
        Converts the loadouts stored in the app configuration into a dictionary format.

        Returns:
            dict: A dictionary containing the loadout data with the following keys:
                  - "Name" (list): The names of the loadout weapons.
                  - "Amp" (list): The amplitudes of the loadout.
                  - "Scope" (list): The scopes of the loadout.
                  - "Sight 1" (list): The first sight of the loadout.
                  - "Sight 2" (list): The second sight of the loadout.
                  - "Damage" (list): The damage enhancements of the loadout.
                  - "Accuracy" (list): The accuracy enhancements of the loadout.
                  - "Economy" (list): The economy enhancements of the loadout.
        """
        d = {"Name": [], "Amp": [], "Scope": [], "Sight 1": [],
                         "Sight 2": [], "Damage": [], "Accuracy": [], "Economy": []}
        for loadout in self.app.config.loadouts.value:
            if isinstance(loadout, list):
                loadout = Loadout(**dict(zip(Loadout.FIELDS, loadout)))
            loadout: Loadout
            d["Name"].append(loadout.weapon)
            d["Amp"].append(loadout.amp)
            d["Scope"].append(loadout.scope)
            d["Sight 1"].append(loadout.sight_1)
            d["Sight 2"].append(loadout.sight_2)
            d["Damage"].append(loadout.damage_enh)
            d["Accuracy"].append(loadout.accuracy_enh)
            d["Economy"].append(loadout.economy_enh)
        return d

    def redraw_weapons(self):
        """
        Redraws the weapons in the GUI.

        This function refreshes the custom weapons, clears the current weapons data, and loads the updated loadout data into the weapons.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        self.refresh_custom_weapons()
        self.weapons.clear()
        self.weapons.setData(self.loadout_to_data())

    def add_new_weapon(self):
        """
        Initializes a new weapon and adds it to the game.

        Parameters:
            self (Game): The instance of the Game class.
        
        Returns:
            None
        """
        weapon_popout = WeaponPopOut(self)
        if self.app.config.theme == "light":
            self.set_stylesheet(weapon_popout, "light.qss")
        else:
            self.set_stylesheet(weapon_popout, "dark.qss")
        self.add_weapon_btn.setEnabled(False)

    def create_weapon(self):
        """
        Create a weapon by initializing a CreateWeaponPopOut object and configuring its stylesheet based on the current theme. Disable the create_weapon_btn button.

        Parameters:
            None

        Returns:
            None
        """
        create_weapon_popout = CreateWeaponPopOut(self)
        if self.app.config.theme == "light":
            self.set_stylesheet(create_weapon_popout, "light.qss")
        else:
            self.set_stylesheet(create_weapon_popout, "dark.qss")
        self.create_weapon_btn.setEnabled(False)

    def add_weapon_cancled(self):
        """
        Add a description of the `add_weapon_canceled` function.

        This function enables the `add_weapon_btn` button.

        Parameters:
            self: The instance of the class.

        Returns:
            None
        """
        self.add_weapon_btn.setEnabled(True)

    def create_weapon_canceled(self):
        """
        Creates a weapon that was canceled.

        Parameters:
            self (ClassName): An instance of the ClassName class.

        Returns:
            None
        """
        self.create_weapon_btn.setEnabled(True)

    def on_added_weapon(self, *args):
        """
        Creates a new loadout based on the given arguments and adds it to the `loadouts` list in the `config` object. Then, saves the `config` object and redraws the weapons.
        
        Parameters:
            *args: The arguments needed to create a new loadout. The order of the arguments must match the order of the fields in the `Loadout` class.
        
        Returns:
            None
        """
        new_loadout = Loadout(**dict(zip(Loadout.FIELDS, args)))
        self.app.config.loadouts.value.append(new_loadout)
        self.app.config.save()
        self.redraw_weapons()

    def on_created_weapon(self, weapon: str, decay: Decimal, ammo_burn: int):
        """
        Adds a new custom weapon to the app's configuration.

        Args:
            weapon (str): The name of the weapon.
            decay (Decimal): The decay value of the weapon.
            ammo_burn (int): The amount of ammo the weapon burns.

        Returns:
            None
        """
        self.app.config.custom_weapons.value.append(CustomWeapon(weapon, decay, ammo_burn))
        self.app.config.save()
        self.redraw_weapons()

    def update_screenshot_fields(self):
        """
        Updates the screenshot-related fields in the application configuration.

        Parameters:
            None

        Returns:
            None
        """
        self.app.config.screenshot_threshold = int(self.screenshot_threshold.text())
        self.app.config.screenshot_delay = int(self.screenshots_delay.text())
        self.app.config.screenshot_directory = self.screenshots_directory_text.text()
        self.app.config.screenshot_enabled = self.screenshots_checkbox.isChecked()

        if not os.path.exists(os.path.expanduser(self.app.config.screenshot_directory.value)):
            os.makedirs(os.path.expanduser(self.app.config.screenshot_directory.value))

    def set_new_streamer_layout(self):
        """
        Set the new layout for the streamer.

        This function sets the new layout for the streamer by updating the streamer_layout configuration parameter. 
        The new layout is obtained by parsing the JSON string provided in the streamer_window_layout_text 
        QTextEdit widget. 

        Parameters:
        - self: The current instance of the class.

        Return:
        - None

        Exceptions:
        - Any exception raised during the parsing of the JSON string will cause the streamer_window_layout_text 
          QTextEdit widget to be styled with red color.
        - If the app.theme is "dark", the streamer_window_layout_text QTextEdit widget will be styled with white 
          color. Otherwise, it will be styled with black color.
        """
        try:
            self.app.config.streamer_layout = json.loads(self.streamer_window_layout_text.toPlainText())
            self.streamer_window_layout_text.setStyleSheet("color: white;" if self.app.theme == "dark" else "color: black;")
        except:
            self.streamer_window_layout_text.setStyleSheet("color: red;")

    def open_files(self):
        """
        Open files using a QFileDialog and set the location in the app config.

        :param self: The object instance.
        :return: None
        """
        path = QFileDialog.getOpenFileName(self, 'Open a file', '', 'All Files (*.*)')
        self.app.config.location = path[0]
        self.chat_location_text.setText(path[0])
        self.onChatLocationChanged()

    def recalculateWeaponFields(self):
        """
        Recalculates the weapon fields based on the selected loadout.

        Params:
            None

        Returns:
            None
        """
        loadout = self.app.config.selected_loadout.value
        if loadout.weapon is None:
            return

        weapon = ALL_WEAPONS[loadout.weapon]
        amp = ALL_ATTACHMENTS.get(loadout.amp)
        ammo = weapon["ammo"] * (1 + (0.1 * loadout.damage_enh)) * (1 - (0.01 * loadout.economy_enh))
        decay = weapon["decay"] * Decimal(1 + (0.1 * loadout.damage_enh)) * Decimal(1 - (0.01 * loadout.economy_enh))
        
        if amp:
            ammo += amp["ammo"]
            decay += amp["decay"]
        self.ammo_burn_text.setText(str(int(ammo)))
        self.weapon_decay_text.setText("%.6f" % decay)

        scope = SCOPES.get(loadout.scope)
        if scope:
            decay += scope["decay"]
            ammo += scope["ammo"]

        sight_1 = SIGHTS.get(loadout.sight_1)
        if sight_1:
            decay += sight_1["decay"]
            ammo += sight_1["ammo"]

        sight_2 = SIGHTS.get(loadout.sight_2)
        if sight_2:
            decay += sight_2["decay"]
            ammo += sight_2["ammo"]

        self.app.combat_module.decay = decay
        self.app.combat_module.ammo_burn = ammo

        self.app.save_config()
        self.app.combat_module.update_active_run_cost()

    def onNameChanged(self):
        """
        Updates the name in the app's configuration and saves the configuration.

        Parameters:
            None

        Returns:
            None
        """
        """
        Updates the name in the app's configuration and saves the configuration.

        Parameters:
            None

        Returns:
            None
        """
        self.app.config.name = self.character_name.text()
        self.app.save_config()

    def onChatLocationChanged(self):
        """
        A function to handle changes in the chat location.

        This function is triggered when the chat location changes. It updates the location
        in the application's configuration.

        Parameters:
            None

        Returns:
            None
        """
        if "*" in self.chat_location_text.text():
            print("Probably an error trying to resave this value, don't update")
            return
        self.app.config.location = self.chat_location_text.text()


class WeaponPopOut(QWidget):
    def __init__(self, parent: ConfigTab):
        super().__init__()

        self.parent = parent

        # this will hide the title bar
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        # set the title
        self.setWindowTitle("Add Weapon")

        # setting  the geometry of window
        self.setGeometry(100, 100, 340, 100)


        self.weapon = ""
        self.amp = "Unamped"
        self.scope = "None"
        self.sight_1 = "None"
        self.sight_2 = "None"
        self.damage_enhancers = 0
        self.accuracy_enhancers = 0
        self.economy_enhancers = 0

        self.layout = self.create_widgets()
        self.resize_to_contents()

        self.show()

    def resize_to_contents(self):
        """
        Resizes the widget to fit its contents.

        This method sets the size of the widget to the size recommended by its layout. It is useful when the widget's size depends on the size of its child widgets or the content it displays.

        Parameters:
            self (QWidget): The widget that will be resized.

        Returns:
            None
        """
        self.setFixedSize(self.layout.sizeHint())

    def create_widgets(self):
        """
        Create and initialize the widgets for the GUI.

        Returns:
            None.
        """
        layout = QVBoxLayout()
        self.setLayout(layout)

        form_inputs = QFormLayout()

        # Weapon Configuration
        self.weapon_option = QComboBox()
        self.weapon_option.addItems(sorted(ALL_WEAPONS))
        form_inputs.addRow("Weapon:", self.weapon_option)
        self.weapon_option.currentIndexChanged.connect(self.on_field_changed)
        self.weapon = self.weapon_option.currentText()

        self.amp_option = QComboBox()
        self.amp_option.addItems(["Unamped"] + sorted(ALL_ATTACHMENTS))
        form_inputs.addRow("Amplifier:", self.amp_option)
        self.amp_option.currentIndexChanged.connect(self.on_field_changed)

        self.scope_option = QComboBox()
        self.scope_option.addItems(["None"] + sorted(SCOPES))
        form_inputs.addRow("Scope:", self.scope_option)
        self.scope_option.currentIndexChanged.connect(self.on_field_changed)

        self.sight_1_option = QComboBox()
        self.sight_1_option.addItems(["None"] + sorted(SIGHTS))
        form_inputs.addRow("Sight 1:", self.sight_1_option)
        self.sight_1_option.currentIndexChanged.connect(self.on_field_changed)

        self.sight_2_option = QComboBox()
        self.sight_2_option.addItems(["None"] + sorted(SIGHTS))
        form_inputs.addRow("Sight 2:", self.sight_2_option)
        self.sight_2_option.currentIndexChanged.connect(self.on_field_changed)

        self.damage_enhancers_txt = QLineEdit(text="0")
        form_inputs.addRow("Damage Enhancers:", self.damage_enhancers_txt)
        self.damage_enhancers_txt.editingFinished.connect(self.on_field_changed)

        self.accuracy_enhancers_txt = QLineEdit(text="0")
        form_inputs.addRow("Accuracy Enhancers:", self.accuracy_enhancers_txt)
        self.accuracy_enhancers_txt.editingFinished.connect(self.on_field_changed)
        layout.addLayout(form_inputs)

        self.economy_enhancers_txt = QLineEdit(text="0")
        form_inputs.addRow("Economy Enhancers:", self.economy_enhancers_txt)
        self.economy_enhancers_txt.editingFinished.connect(self.on_field_changed)
        layout.addLayout(form_inputs)

        h_layout = QHBoxLayout()

        cancel = QPushButton("Cancel")
        cancel.released.connect(self.cancel)

        confirm = QPushButton("Confirm")
        confirm.released.connect(self.confirm)

        h_layout.addWidget(cancel)
        h_layout.addWidget(confirm)

        layout.addLayout(h_layout)

        layout.addStretch()
        return layout

    def cancel(self):
        """
        Cancels the current operation.

        This function is responsible for canceling the current operation. It performs the following steps:
        1. Calls the `add_weapon_canceled` method of the parent object to indicate that the weapon has been canceled.
        2. Closes the current operation.

        Parameters:
            self: The instance of the class.

        Returns:
            None
        """
        self.parent.add_weapon_cancled()
        self.close()

    def confirm(self):
        """
        Confirms the weapon selection and adds it to the parent object.

        This method is called when the confirmation button is pressed. It checks if a weapon is selected. If no weapon is selected, it closes the weapon selection window. If a weapon is selected, it calls the `on_added_weapon` method of the parent object with the selected weapon and other related parameters.

        Parameters:
            None.

        Returns:
            None.
        """
        if not self.weapon:
            self.close()
        self.parent.on_added_weapon(
            self.weapon,
            self.amp,
            self.scope,
            self.sight_1,
            self.sight_2,
            self.damage_enhancers,
            self.accuracy_enhancers,
            self.economy_enhancers
        )
        self.close()

    def on_field_changed(self):
        """
        Updates the attributes of the object based on the selected options in the GUI.

        Parameters:
            self (object): The instance of the class.
        
        Returns:
            None
        """
        self.scope = self.scope_option.currentText()
        self.sight_1 = self.sight_1_option.currentText()
        self.sight_2 = self.sight_2_option.currentText()
        self.weapon = self.weapon_option.currentText()
        self.amp = self.amp_option.currentText()
        self.damage_enhancers = min(10, int(self.damage_enhancers_txt.text()))
        self.accuracy_enhancers = min(10, int(self.accuracy_enhancers_txt.text()))
        self.economy_enhancers = min(10, int(self.economy_enhancers_txt.text()))

        self.damage_enhancers_txt.setText(str(self.damage_enhancers))
        self.accuracy_enhancers_txt.setText(str(self.accuracy_enhancers))
        self.economy_enhancers_txt.setText(str(self.economy_enhancers))

    def mousePressEvent(self, event):
        """
        A function that handles the mouse press event.

        Args:
            event (QMouseEvent): The mouse event object containing information about the event.

        Returns:
            None: This function does not return anything.
        """
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        """
        Handles the mouse move event.

        Args:
            event (QMouseEvent): The mouse event object.

        Returns:
            None
        """
        delta = QPoint (event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def closeEvent(self, event):
        """
        Close the event.

        Args:
            event: The event object.

        Returns:
            None
        """
        event.accept()  # let the window close


class CreateWeaponPopOut(QWidget):
    def __init__(self, parent: ConfigTab):
        super().__init__()

        self.parent = parent

        # this will hide the title bar
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        # set the title
        self.setWindowTitle("Add Weapon")

        # setting  the geometry of window
        self.setGeometry(100, 100, 340, 100)

        self.layout = self.create_widgets()
        self.resize_to_contents()

        self.show()

    def resize_to_contents(self):
        """
        Resizes the widget to fit its contents.

        This method sets the fixed size of the widget based on the size hint of its layout. 
        The widget will expand or shrink to accommodate the size of its contents.

        Parameters:
            None

        Returns:
            None
        """
        self.setFixedSize(self.layout.sizeHint())

    def create_widgets(self):
        """
        Creates and returns a layout containing a form for creating widgets.

        Returns:
            QVBoxLayout: The layout containing the form.
        """
        layout = QVBoxLayout()
        self.setLayout(layout)

        form_inputs = QFormLayout()

        self.weapon_name_txt = QLineEdit(text="<Item Name>")
        form_inputs.addRow("Weapon Name:", self.weapon_name_txt)
        self.weapon_name_txt.editingFinished.connect(self.on_field_changed)

        self.ammo_burn_txt = QLineEdit(text="0")
        form_inputs.addRow("Ammo Burn:", self.ammo_burn_txt)
        self.ammo_burn_txt.editingFinished.connect(self.on_field_changed)

        self.decay_txt = QLineEdit(text="0.0")
        form_inputs.addRow("Decay (PED):", self.decay_txt)
        self.decay_txt.editingFinished.connect(self.on_field_changed)
        layout.addLayout(form_inputs)

        h_layout = QHBoxLayout()

        cancel = QPushButton("Cancel")
        cancel.released.connect(self.cancel)

        confirm = QPushButton("Confirm")
        confirm.released.connect(self.confirm)

        h_layout.addWidget(cancel)
        h_layout.addWidget(confirm)

        layout.addLayout(h_layout)

        layout.addStretch()
        return layout

    def cancel(self):
        """
        Cancels the current operation.

        This function is responsible for canceling the operation. It calls the `create_weapon_canceled` method of the `parent` object to notify it that the weapon creation process has been canceled. After that, it closes the current operation.

        Parameters:
            self (ClassName): The instance of the class that this method belongs to.

        Returns:
            None
        """
        self.parent.create_weapon_canceled()
        self.close()

    def confirm(self):
        """
        Confirm the creation of a weapon.

        This function notifies the parent object about the creation of a weapon by calling the `on_created_weapon` method. It passes the weapon's name, decay, and burn as parameters to the parent object.

        Parameters:
            None

        Returns:
            None
        """
        self.parent.on_created_weapon(
            self.name,
            self.weapon_decay,
            self.weapon_burn
        )
        self.close()

    def on_field_changed(self):
        """
        Update the attributes of the weapon based on the user input.

        This function is called whenever a field is changed in the UI. It retrieves the values from the input fields and updates the corresponding attributes of the weapon. The updated attributes include the name, decay, and burn rate of the weapon.

        Parameters:
        - None

        Return:
        - None
        """
        self.name = self.weapon_name_txt.text()
        self.weapon_decay = self.decay_txt.text()
        self.weapon_burn = int(self.ammo_burn_txt.text())

    def mousePressEvent(self, event):
        """
        Sets the position of the mouse when a mouse press event occurs.

        Parameters:
            event (QMouseEvent): The mouse press event.

        Returns:
            None
        """
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        """
        Handles the mouse move event.

        Args:
            event (QMouseEvent): The mouse move event.

        Returns:
            None
        """
        delta = QPoint (event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def closeEvent(self, event):
        """
        Handle the close event of the window and accept it to close the window.

        Args:
            event: The close event triggered by the user.

        Returns:
            None
        """
        event.accept()  # let the window close
