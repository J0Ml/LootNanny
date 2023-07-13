from PyQt5.QtWidgets import QStatusBar, QFormLayout, QHeaderView, QTabWidget, QCheckBox, QGridLayout, QComboBox, QLineEdit, QLabel, QApplication, QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import QFile, QTextStream
import pyqtgraph as pg
import traceback
from datetime import datetime
import webbrowser
from decimal import Decimal

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))

from errors import log_crash
try:
    from helpers import resource_path
    from utils.tables import *
    from modules.combat import CombatModule
    from views.configuration import ConfigTab
    from config import Config
    from chat import ChatReader
    from version import VERSION
    from windows.streamer import StreamerWindow
    from views.twitch import TwitchTab
    from modules.combat import MarkupSingleton
    from views.crafting import CraftingTab
except Exception as e:
    log_crash(e)

MAIN_EVENT_LOOP_TICK = 0.1
TICK_COUNTER = 0

class LootNanny(QWidget):

    def __init__(self):
        super().__init__()
        self.config = Config()

        # Other Windows
        self.streamer_window = None
        self.streamer_window_btn = QPushButton("Show Streamer UI")
        self.streamer_window_btn.released.connect(self.on_toggle_streamer_ui)

        self.setWindowTitle("Loot Nanny")
        self.resize(600, 320)
        # Create a top-level layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Modules
        self.combat_module = CombatModule(self)

        self.config_tab = ConfigTab(self)

        self.chat_reader = ChatReader(self)

        # Create the tab widget with two tabs
        tabs = QTabWidget()
        tabs.addTab(self.lootTabUI(), "Loot")
        tabs.addTab(self.analysisTabUI(), "Analysis")
        tabs.addTab(self.skillTabUI(), "Skills")
        tabs.addTab(self.combatTabUI(), "Combat")
        self.twitch = TwitchTab(self, self.config)
        self.crafting = CraftingTab(self)
        tabs.addTab(self.crafting, "Crafting")
        tabs.addTab(self.twitch, "Twitch")

        tabs.addTab(self.config_tab, "Config")
        layout.addWidget(tabs)

        statusBar = QStatusBar()

        self.logging_toggle_btn = QPushButton("Start Run")
        self.logging_toggle_btn.setStyleSheet("background-color: green")
        self.logging_toggle_btn.released.connect(self.on_toggle_logging)

        self.logging_pause_btn = QPushButton("Pause Logging", enabled=False)
        self.logging_pause_btn.setStyleSheet("background-color: grey; color: white;")
        self.logging_pause_btn.released.connect(self.on_pause_logging)

        statusBar.addWidget(QLabel(f"Version: {VERSION}"))

        statusBar.addWidget(self.logging_toggle_btn)
        statusBar.addWidget(self.logging_pause_btn)

        statusBar.addWidget(self.streamer_window_btn)

        self.theme = "dark"
        self.theme_btn = QPushButton("Toggle Theme")
        self.theme_btn.clicked.connect(lambda: self.toggle_stylesheet())
        self.theme_btn.setStyleSheet("background-color: white; color: black;")

        self.donate_btn = QPushButton("Donate :)")
        self.donate_btn.setStyleSheet("background-color: blue;")
        self.donate_btn.released.connect(self.open_donation_window)
        statusBar.addWidget(self.donate_btn)

        statusBar.addWidget(self.theme_btn)

        self.combat_module.load_runs()
        layout.addWidget(statusBar)

        self.initialize_from_config()

    def open_donation_window(self):
        """
        Opens a donation window by opening the specified URL in a web browser.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        url = "https://www.paypal.com/donate?hosted_button_id=QN5CN9A52Q59E"
        webbrowser.open(url, new=0)

    def initialize_from_config(self):
        """
        Initializes the object based on the provided configuration.

        Returns:
            None
        """
        if not self.config:
            return

        if self.config.theme.value == "light":
            self.set_stylesheet(self, "light.qss")
            self.theme_btn.setStyleSheet("background-color: #222222; color: white;")

    def save_config(self):
        """
        Saves the configuration.

        This function saves the current configuration by calling the `save()` method of the `config` object.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None: This function does not return anything.
        """
        self.config.save()

    def on_toggle_streamer_ui(self):
        """
        Toggles the visibility of the streamer UI window.

        If the streamer window is currently open, it will be closed. If it is closed, a new
        streamer window will be created and displayed. The appearance of the streamer window
        will depend on the current theme.

        Parameters:
            None

        Returns:
            None
        """
        if self.streamer_window:
            self.streamer_window.close()
            self.streamer_window = None
        else:
            self.streamer_window = StreamerWindow(self)
            if self.theme == "light":
                self.set_stylesheet(self.streamer_window, "light.qss")
            else:
                self.set_stylesheet(self.streamer_window, "dark.qss")

    def on_toggle_logging(self):
        """
        Toggles logging on or off.

        This function is called when the logging toggle button is pressed. It checks the current state of the logging module and performs the appropriate actions to toggle logging on or off.

        Parameters:
        - self: The instance of the class.

        Returns:
        - None
        """
        if self.combat_module.is_logging:
            self.combat_module.is_logging = False
            self.combat_module.is_paused = False
            self.combat_module.active_run.time_end = datetime.now()
            self.combat_module.active_run = None
            self.logging_toggle_btn.setStyleSheet("background-color: green")
            self.logging_toggle_btn.setText("Start Run")
            self.logging_pause_btn.setEnabled(False)
            self.logging_pause_btn.setText("Pause Logging")
            self.logging_pause_btn.setStyleSheet("background-color: grey: color; white;")
            self.combat_module.save_active_run(force=True)
            self.combat_module.update_tables()
        else:
            self.combat_module.is_logging = True
            self.combat_module.is_paused = False
            self.logging_toggle_btn.setStyleSheet("background-color: red")
            self.logging_toggle_btn.setText("End Run")
            self.logging_pause_btn.setEnabled(True)
            self.logging_pause_btn.setText("Pause Logging")
            self.logging_pause_btn.setStyleSheet("background-color: green")

    def on_pause_logging(self):
        """
        Toggles logging on and off.

        This function checks if the combat module is currently paused. If it is paused, it resumes logging by setting the `is_paused` attribute to False. It also updates the styling of the `logging_pause_btn` button to have a green background color and changes the button text to "Pause Logging". Additionally, it saves the active run of the combat module.

        If the combat module is not paused, this function pauses logging by setting the `is_paused` attribute to True. It updates the styling of the `logging_pause_btn` button to have a red background color and changes the button text to "Unpause Logging". It also saves the active run of the combat module.

        Parameters:
            self (object): The instance of the class calling the function.

        Return:
            None
        """
        if self.combat_module.is_paused:
            self.combat_module.is_paused = False
            self.logging_pause_btn.setStyleSheet("background-color: green")
            self.logging_pause_btn.setText("Pause Logging")
            self.combat_module.save_active_run(force=True)
        else:
            self.combat_module.is_paused = True
            self.logging_pause_btn.setStyleSheet("background-color: red")
            self.logging_pause_btn.setText("Unpause Logging")
            self.combat_module.save_active_run(force=True)

    def on_tick(self):
        """
        Executes the on_tick function.

        This function is called on every tick of the program. It performs the following actions:
        1. Increments the TICK_COUNTER global variable.
        2. Resets the TICK_COUNTER to 0 if it is divisible by 5.
        3. Calls the `delay_start_reader` method of the `chat_reader` object.
        4. Retrieves all recent lines in the chat and stores them in the `all_lines_this_tick` list.
        5. Processes the lines in the `all_lines_this_tick` list incrementally using the `tick` method of the `combat_module` object.
        6. Resizes the `streamer_window` if it exists.

        Raises:
            Exception: If an error occurs during the execution of the function.

        """
        global TICK_COUNTER
        try:
            TICK_COUNTER += 1
            if not TICK_COUNTER % 5:
                TICK_COUNTER %= 5

            self.chat_reader.delay_start_reader()

            # Grab all recent lines in the chat and process them incrementally
            all_lines_this_tick = []
            while True:
                line = self.chat_reader.getline()
                if not line or len(all_lines_this_tick) > 5:
                    break
                all_lines_this_tick.append(line)

            self.combat_module.tick(all_lines_this_tick)

            if self.streamer_window:
                self.streamer_window.resize_to_contents()

        except Exception as e:
            traceback.print_exc()
            print(e)

    def lootTabUI(self):
        """Create the General page UI."""
        generalTab = QWidget()

        layout = QVBoxLayout()

        # Create a QFormLayout instance
        form_inputs = QFormLayout()
        # Add widgets to the layout

        looted_text = QLineEdit(enabled=False)
        form_inputs.addRow("Creatures Looted:", looted_text)

        total_cost_text = QLineEdit(enabled=False)
        form_inputs.addRow("Total Cost:", total_cost_text)

        total_return_text = QLineEdit(enabled=False)
        form_inputs.addRow("Total Return:", total_return_text)

        return_perc_text = QLineEdit(enabled=False)
        form_inputs.addRow("% Return:", return_perc_text)

        globals = QLineEdit(enabled=False)
        form_inputs.addRow("Globals:", globals)

        hofs = QLineEdit(enabled=False)
        form_inputs.addRow("HOFs:", hofs)

        self.item_table = LootTableView({"Item": [], "Value": [], "Count": [], "Markup": [], "Total Value": []}, 100, 5)
        self.runs = RunsView({"Notes": [], "Start": [], "End": [], "Spend": [], "Enhancers": [],
                         "Extra Spend": [], "Return": [], "%": [], "mu%": []}, 40, 9)
        self.runs.itemClicked.connect(self.onLootTableClicked)
        self.runs.model().dataChanged.connect(self.onRunsChanged)

        self.item_table.itemClicked.connect(self.on_loot_item_selected)
        self.item_table.model().dataChanged.connect(self.on_markup_changed)

        # Run Management buttons
        self.delete_run_button = QPushButton("Delete Run", enabled=False)
        self.delete_run_button.setStyleSheet("background-color: #f06c6c; color: black;")
        self.delete_run_button.released.connect(self.delete_runs)
        self.delete_run_button.hide()

        self.combat_module.loot_table = self.item_table
        self.combat_module.runs_table = self.runs
        self.combat_module.loot_fields = {
            "looted_text": looted_text,
            "total_cost_text": total_cost_text,
            "total_return_text": total_return_text,
            "return_perc_text": return_perc_text,
            "globals": globals,
            "hofs": hofs
        }

        # eulogger.table_view = table
        layout.addLayout(form_inputs)
        layout.addWidget(self.runs)
        layout.addWidget(self.delete_run_button)
        layout.addWidget(self.item_table)

        generalTab.setLayout(layout)
        return generalTab

    def onRunsChanged(self):
        """
        Updates the selected runs in the GUI with the corresponding data from the UI.

        This function is triggered when the selection of runs in the GUI changes. It retrieves
        the indexes of the selected rows in the `runs` table view. If there are no selected rows,
        the function returns early. Otherwise, it determines the changed row and its corresponding
        index in the `combat_module.runs` list.

        The function then retrieves the `notes` and `extra_spend` cells for the changed row from
        the `runs` table view. It attempts to convert the text in the `extra_spend` cell to a
        decimal value. If the conversion fails, the default value of 0.0 is used and the `extra_spend`
        cell is set to "0.0". 

        Finally, the function updates the `extra_spend` and `notes` attributes of the corresponding
        run object in the `combat_module.runs` list. It sets the `should_redraw_runs` flag of the
        `combat_module` to True and clears the selection in the `runs` table view.
        """
        indexes = self.runs.selectionModel().selectedRows()
        if not indexes:
            return
        changed = [(i.row(), len(self.combat_module.runs) - 1 - i.row()) for i in indexes][0]
        notes_cell = self.runs.item(changed[0], 0)
        spend_cell = self.runs.item(changed[0], 5)
        try:
            extra_spend = Decimal(spend_cell.text() or "0")
        except:
            extra_spend = 0.0
            spend_cell.setText("0.0")
        self.combat_module.runs[changed[1]].extra_spend = extra_spend
        self.combat_module.runs[changed[1]].notes = notes_cell.text()
        self.combat_module.should_redraw_runs = True
        self.clear_run_selection()

    def on_markup_changed(self):
        """
        Handle the event when the markup is changed.
        
        This function is triggered when the markup in the item table is changed. It performs the following steps:
        
        1. Get the selected rows from the item table.
        2. If no rows are selected, return.
        3. Get the index of the first selected row.
        4. Get the name and markup cells of the selected row.
        5. Add the markup for the item to the MarkupSingleton.
        6. Update the loot table in the combat module.
        7. Clear the selection in the loot item table.
        """
        selected_rows = self.item_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        selected_row = selected_rows[0].row()
        name_cell = self.item_table.item(selected_row, 0)
        markup_cell = self.item_table.item(selected_row, 3)
        MarkupSingleton.add_markup_for_item(name_cell.text(), markup_cell.text())
        self.combat_module.update_loot_table()
        self.clear_loot_item_table_selection()

    def on_loot_item_selected(self):
        """
        A function that handles the event when a loot item is selected.

        Parameters:
            None

        Returns:
            None
        """
        indexes = self.item_table.selectionModel().selectedRows()
        if not indexes:
            return
        self.loot_item_to_change = [len(self.combat_module.runs) - 1 - i.row() for i in indexes][0]

    def clear_loot_item_table_selection(self):
        """
        Clears the selection in the loot item table.

        Parameters:
            None

        Returns:
            None
        """
        self.item_table.selectionModel().clearSelection()

    def clear_run_selection(self):
        """
        Clears the selection of runs in the runs table.
        """
        self.runs.selectionModel().clearSelection()
        self.delete_run_button.hide()

    def onLootTableClicked(self):
        """
        Handles the click event on the loot table.
        Retrieves the selected rows from the loot table and updates the delete run button accordingly.
        
        Parameters:
            self (object): The instance of the class.
        
        Returns:
            None
        """
        self.delete_run_button.show()

        indexes = self.runs.selectionModel().selectedRows()
        if not indexes:
            return
        if len(indexes) > 1:
            self.delete_run_button.setText("Delete Runs")
        else:
            self.delete_run_button.setText("Delete Run")

        self.delete_run_button.setEnabled(True)

        self.runs_rows_to_delete = [len(self.combat_module.runs) - 1 - i.row() for i in indexes]

    def delete_runs(self):
        """
        Deletes the selected runs from the combat module.

        This function iterates over the runs in the combat module and removes the runs that are marked for deletion. The runs that are not marked for deletion are copied to a new list called `copy_runs`. The `runs_rows_to_delete` variable is then reset to an empty list. The delete button is disabled and hidden. The selection in the runs table is cleared. The `combat_module.runs` is updated to contain the runs in `copy_runs`. If the active run is not in `copy_runs`, it is set to `None`. The runs table is cleared and the runs table is updated. Finally, the runs are saved and the run selection is cleared.
        """
        copy_runs = []
        for i, run in enumerate(self.combat_module.runs):
            if i in self.runs_rows_to_delete:
                continue
            copy_runs.append(run)
        self.runs_rows_to_delete = []
        self.delete_run_button.setEnabled(False)
        self.delete_run_button.hide()
        self.runs.clearSelection()
        self.combat_module.runs = copy_runs
        if self.combat_module.active_run not in copy_runs:
            self.combat_module.active_run = None
        self.runs.clear()
        self.combat_module.update_runs_table()
        self.combat_module.save_runs(force=True)
        self.clear_run_selection()

    def analysisTabUI(self):
        """
        Generates the UI for the analysis tab.

        :return: QWidget object representing the analysis tab UI.
        """
        analysisTab = QWidget()
        layout = QVBoxLayout()

        return_graph = pg.PlotWidget()
        return_graph.plot([])
        return_graph.setTitle("Run TT Return (%)")
        return_graph.setLabel('left', 'Return (%)')

        multi_graph = pg.PlotWidget()
        multi_graph.plot([])
        multi_graph.setTitle("Cost to kill vs Return")
        multi_graph.setLabel('bottom', 'Cost To Kill (PED)')
        multi_graph.setLabel('left', 'Return (PED)')

        self.combat_module.multiplier_graph = multi_graph
        self.combat_module.return_graph = return_graph
        layout.addWidget(return_graph)
        layout.addWidget(multi_graph)
        analysisTab.setLayout(layout)
        return analysisTab

    def skillTabUI(self):
        """Create the General page UI."""
        skillTab = QWidget()

        layout = QVBoxLayout()

        # Create a QFormLayout instance
        form_inputs = QFormLayout()
        # Add widgets to the layout

        self.total_skills_text = QLineEdit(enabled=False)
        form_inputs.addRow("Total Skill Gain:", self.total_skills_text)

        table = SkillTableView({"Skill": [], "Value": [], "Proc": [], "Proc %": []}, 40, 4)

        # eulogger.skill_table = table
        layout.addLayout(form_inputs)
        layout.addWidget(table)

        skillTab.setLayout(layout)
        self.combat_module.skill_table = table
        return skillTab

    def combatTabUI(self):
        """Create the Network page UI."""

        combatTab = QWidget()

        layout = QVBoxLayout()

        form_inputs = QFormLayout()

        shots_text = QLineEdit(enabled=False)
        form_inputs.addRow("Shots Fired:", shots_text)

        damage_text = QLineEdit(enabled=False)
        form_inputs.addRow("Total Damage:", damage_text)

        critical_rate = QLineEdit(enabled=False)
        form_inputs.addRow("Critical Chance:", critical_rate)

        miss_rate = QLineEdit(enabled=False)
        form_inputs.addRow("Miss Chance:", miss_rate)

        dpp = QLineEdit(enabled=False)
        form_inputs.addRow("dpp:", dpp)

        table = EnhancerTableView({"Enhancer": [], "Breaks": []}, 10, 2)

        self.combat_module.combat_fields = {
            "attacks": shots_text,
            "damage": damage_text,
            "crits": critical_rate,
            "misses": miss_rate,
            "dpp": dpp,
            "enhancer_table": table
        }
        self.combat_module.enhancer_table = table

        layout.addLayout(form_inputs)
        layout.addWidget(table)

        combatTab.setLayout(layout)
        return combatTab

    def toggle_stylesheet(self):
        '''
        Toggle the stylesheet to use the desired path in the Qt resource
        system (prefixed by `:/`) or generically (a path to a file on
        system).

        :path:      A full path to a resource or file on system
        '''
        if self.theme == "light":
            self.theme_btn.setStyleSheet("background-color: #222222; color: white;")
            self.theme = "dark"
            path = "dark.qss"
        else:
            self.theme_btn.setStyleSheet("background-color: white; color: black;")
            self.theme = "light"
            path = "light.qss"

        # get the QApplication instance,  or crash if not set
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No Qt Application found.")

        self.set_stylesheet(self, path)

    def set_stylesheet(self, target, path):
        """
        Sets the stylesheet for a given target widget.

        Args:
            target (QWidget): The target widget to apply the stylesheet to.
            path (str): The path to the stylesheet file.

        Returns:
            None
        """
        file = QFile(resource_path(path))
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        target.setStyleSheet(stream.readAll())

        self.save_config()

    def closeEvent(self, event):
        print("Close Event")
        self.combat_module.save_active_run(force=True)
        """
        Handle the close event triggered by the user.

        Args:
            event (QCloseEvent): The close event object.

        Returns:
            None
        """
        if self.streamer_window:
            self.streamer_window.close()
        if self.twitch.twitch_bot:
            pass # Clean tidy up needed
        event.accept()

def create_ui():
    """
    Creates and displays the user interface for the application.
    
    This function initializes the QApplication object and sets the style to 'Fusion'.
    It then creates an instance of the LootNanny class and sets the stylesheet to "dark.qss".
    The window is then displayed using the show() method.
    
    A QTimer object is created and connected to the on_tick() method of the window instance.
    The timer is started with a timeout value of MAIN_EVENT_LOOP_TICK * 1000 milliseconds.
    
    Finally, the application's event loop is started using the exec() method.
    """
    app = QApplication([])
    app.setStyle('Fusion')

    window = LootNanny()
    window.set_stylesheet(window, "dark.qss")
    window.show()

    timer = QtCore.QTimer()
    timer.timeout.connect(window.on_tick)
    timer.start(int(MAIN_EVENT_LOOP_TICK * 1000)) #timer.start((MAIN_EVENT_LOOP_TICK * 1000)) added int to make it work properly 

    app.exec()

if __name__ == "__main__":
    create_ui()
