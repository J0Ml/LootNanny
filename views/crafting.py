import os
import json
import webbrowser
import time
from decimal import Decimal

from PyQt5.QtWidgets import QFileDialog, QTextEdit, QHBoxLayout, QFormLayout, QHeaderView, QTabWidget, QCheckBox, QGridLayout, QComboBox, QLineEdit, QLabel, QApplication, QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem

from data.crafting import ALL_RESOURCES, ALL_BLUEPRINTS
from utils.tables import CraftingTableView
from modules.combat import MarkupSingleton


class CraftingTab(QWidget):

    def __init__(self, app: "LootNanny", *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app = app

        # Operational Inputs
        self.selected_blueprint = None
        self.blueprint_markup = Decimal("0.0")
        self.total_clicks = 1
        self.total_tt_cost = Decimal("0.0")
        self.total_cost = Decimal("0.0")
        self.max_tt = Decimal("100.00")

        self.use_residue = False
        self.one_item_per_success = False
        self.residue_markup = Decimal("1.02")

        self.blueprint_table_selected_row = None
        self.blueprint_table = None

        self.create_layout()

    def create_layout(self):
        """
        Creates the layout for the GUI.
        
        Returns:
            None
        """
        layout = QVBoxLayout()

        form_inputs = QFormLayout()
        layout.addLayout(form_inputs)

        # Weapon Configuration
        self.bp_option = QComboBox()
        self.bp_option.addItems(sorted(ALL_BLUEPRINTS))
        form_inputs.addRow("Blueprint:", self.bp_option)
        self.bp_option.currentIndexChanged.connect(self.on_blueprint_changed)

        # Blueprint Table View
        # ("Resource", "Amount", "TT Cost", "Markup", "Total Cost")
        self.blueprint_table = CraftingTableView({"Resource": [], "Per Click": [], "Total": [], "TT Cost": [],
                                                  "Markup": [], "Total Cost": []}, 10, 6)
        self.blueprint_table.itemClicked.connect(self.on_bluprint_table_selected)
        self.blueprint_table.model().dataChanged.connect(self.on_blueprint_table_changed)

        form_inputs.addRow("Materials", self.blueprint_table)

        self.total_clicks_text = QLineEdit(text="1", enabled=True)
        form_inputs.addRow("Total Clicks:", self.total_clicks_text)
        self.total_clicks_text.textChanged.connect(self.on_updated_total_clicks)

        self.use_residue_check = QCheckBox()
        self.use_residue_check.setChecked(self.use_residue)
        self.use_residue_check.toggled.connect(self.use_residue_toggled)
        form_inputs.addRow("Use Residue:", self.use_residue_check)

        self.one_item_per_success_check = QCheckBox()
        self.one_item_per_success_check.setChecked(self.one_item_per_success)
        self.one_item_per_success_check.toggled.connect(self.one_item_per_success_check_toggled)
        form_inputs.addRow("OVERRIDE: 1 Item Per Success:", self.one_item_per_success_check)

        self.item_max_tt = QLineEdit(text="100.00", enabled=True)
        form_inputs.addRow("Item Max TT:", self.item_max_tt)
        self.item_max_tt.textChanged.connect(self.item_max_tt_text_changed)

        self.residue_markup_text = QLineEdit(text="102%", enabled=True)
        form_inputs.addRow("Residue Markup:", self.residue_markup_text)
        self.residue_markup_text.textChanged.connect(self.residue_markup_text_changed)

        self.blueprint_markup_text = QLineEdit(text="0.00%", enabled=True)
        form_inputs.addRow("Blueprint Markup:", self.blueprint_markup_text)
        self.blueprint_markup_text.textEdited.connect(self.on_changed_blueprint_markup)

        self.residue_required_text = QLineEdit(text="00.00 PED", enabled=False)
        form_inputs.addRow("Residue Required:", self.residue_required_text)

        self.total_tt_cost_text = QLineEdit(text="", enabled=False)
        form_inputs.addRow("TT Cost:", self.total_tt_cost_text)

        self.total_cost_text = QLineEdit(text="", enabled=False)
        form_inputs.addRow("Total Cost:", self.total_cost_text)

        self.add_crafting_run_btn = QPushButton("Add Run To Active Run")
        self.add_crafting_run_btn.released.connect(self.add_crafting_run)
        form_inputs.addWidget(self.add_crafting_run_btn)

        self.default_success_percentage_text = QLineEdit(text="42.00%", enabled=False)
        form_inputs.addRow("Quantity Success %:", self.default_success_percentage_text)

        self.item_markup = QLineEdit(text="100.00%", enabled=True)
        form_inputs.addRow("Item Markup:", self.item_markup)
        self.item_markup.textEdited.connect(self.on_changed_item_markup)

        self.exepcted_successes = QLineEdit(text="0", enabled=False)
        form_inputs.addRow("Expected Successes:", self.exepcted_successes)

        self.tt_as_final_item = QLineEdit(text="00.00 PED", enabled=False)
        form_inputs.addRow("Success TT Value:", self.tt_as_final_item)

        self.expected_near_success_text = QLineEdit(text="00.00 PED", enabled=False)
        form_inputs.addRow("Partials TT Value:", self.expected_near_success_text)

        self.expected_return = QLineEdit(text="00.00 PED", enabled=False)
        form_inputs.addRow("Expected Returns:", self.expected_return)

        self.minimum_markup = QLineEdit(text="00.00 PED", enabled=False)
        form_inputs.addRow("Breakeven Markup:", self.minimum_markup)

        layout.addStretch()
        self.setLayout(layout)

    def one_item_per_success_check_toggled(self):
        """
        Sets the value of the `one_item_per_success` attribute to the value of the `isChecked()` method of the `one_item_per_success_check` object. 
        Calls the `calculate_crafting_totals()` method.
        """
        self.one_item_per_success = self.one_item_per_success_check.isChecked()
        self.calculate_crafting_totals()

    def use_residue_toggled(self):
        """
        Toggles the use_residue attribute of the class instance.
        
        This function is called when the use_residue_check checkbox is toggled. It updates the value of the use_residue attribute by getting the checked state of the checkbox. After updating the attribute, it calls the calculate_crafting_totals() function to recalculate the crafting totals based on the new value of use_residue.
        """
        self.use_residue = self.use_residue_check.isChecked()
        self.calculate_crafting_totals()

    def residue_markup_text_changed(self):
        """
        Updates the `residue_markup` attribute based on the value entered in the `residue_markup_text` field.

        Parameters:
            self (object): The instance of the class.
        
        Returns:
            None
        """
        self.residue_markup = Decimal(self.residue_markup_text.text().replace("%", "")) / 100
        self.calculate_crafting_totals()

    def item_max_tt_text_changed(self):
        """
        Update the value of `self.max_tt` based on the text entered in `self.item_max_tt`.
        Recalculate the crafting totals after updating `self.max_tt`.
        """
        self.max_tt = Decimal(self.item_max_tt.text())
        self.calculate_crafting_totals()

    def get_selected_item_name(self):
        """
        Returns the name of the selected item.
        
        This function checks if a blueprint is selected and if so, it returns the name of the blueprint without the " Blueprint" suffix. If the name contains a level indicator, it removes it as well.
        
        :return: The name of the selected item if a blueprint is selected, or None if no blueprint is selected.
        :rtype: str or None
        """
        if self.selected_blueprint:
            return self.selected_blueprint.replace(" Blueprint", "").rsplit(" (L)", 1)[0]
        return None

    def on_changed_item_markup(self):
        """
        Update the item markup when the selected item changes.

        This function retrieves the name of the selected item using the 
        `get_selected_item_name()` method. If no item is selected, the function 
        returns without performing any further actions.

        The function then calls the `add_markup_for_item()` method of the 
        `MarkupSingleton` class to add the markup for the selected item, using the
        `item_markup.text()` value as the markup. 

        Next, the function updates the data in the `blueprint_table` by calling 
        the `setData()` method with the formatted resources obtained from the 
        current selection.

        Finally, the function calls the `calculate_crafting_totals()` method to 
        calculate the crafting totals.

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        item = self.get_selected_item_name()
        if not item:
            return
        MarkupSingleton.add_markup_for_item(item, self.item_markup.text())
        self.blueprint_table.setData(self.format_resources_from_selection())
        self.calculate_crafting_totals()

    def on_changed_blueprint_markup(self):
        """
        Add a markup for the selected blueprint and calculate crafting totals.

        This function adds a markup for the selected blueprint by calling the `add_markup_for_item` method of the `MarkupSingleton` class. It takes no parameters and does not return any value.

        Parameters:
            None

        Returns:
            None
        """
        MarkupSingleton.add_markup_for_item(self.selected_blueprint, self.blueprint_markup_text.text())
        self.calculate_crafting_totals()

    def add_crafting_run(self):
        """
        Adds a crafting run to the active combat run.

        If there is no active combat run, the function returns without doing anything.

        The function appends a note to the active combat run's notes, indicating the number of clicks and the selected blueprint.
        The note is in the format "+(total_clicks) clicks of (selected_blueprint); ".

        The function updates the total cost and extra spend of the active combat run.
        The total cost is incremented by the total TT cost of the crafting run.
        The extra spend is incremented by the difference between the total cost and the total TT cost.

        After adding the crafting run, the function resets the selected blueprint, total clicks, and blueprint table.

        Finally, the function sets a flag to redraw the runs in the combat module.

        Parameters:
        None

        Returns:
        None
        """
        if not self.app.combat_module.active_run:
            return
        note = f"+({self.total_clicks}) clicks of {self.selected_blueprint}; "
        self.app.combat_module.active_run.notes += note
        self.app.combat_module.active_run.total_cost += self.total_tt_cost
        self.app.combat_module.active_run.extra_spend += self.total_cost - self.total_tt_cost
        self.selected_blueprint = None
        self.total_clicks = 1
        self.blueprint_table.clear()
        self.app.combat_module.should_redraw_runs = True

    def on_updated_total_clicks(self):
        """
        Updates the value of the 'total_clicks' attribute based on the text entered in the 'total_clicks_text' QLineEdit widget. If the text cannot be converted to an integer, the 'total_clicks' attribute is set to 1 and the 'total_clicks_text' widget is updated with the value '1'. After updating the 'total_clicks' attribute, the function calls the 'calculate_crafting_totals' method and updates the data in the 'blueprint_table' widget with the formatted resources obtained from the current selection.
        """
        try:
            self.total_clicks = int(self.total_clicks_text.text())
        except:
            self.total_clicks = 1
            self.total_clicks_text.setText("1")
        self.calculate_crafting_totals()
        self.blueprint_table.setData(self.format_resources_from_selection())

    def calculate_crafting_totals(self):
        self.total_tt_cost = Decimal("0.0")
        self.total_cost = Decimal("0.0")
        if self.selected_blueprint:
            for slot in ALL_BLUEPRINTS[self.selected_blueprint].slots:
                self.total_tt_cost += slot.count * ALL_RESOURCES[slot.name] * self.total_clicks
                self.total_cost += MarkupSingleton.apply_markup_to_item(slot.name,
                                                                        slot.count,
                                                                        slot.count * ALL_RESOURCES[slot.name]) * self.total_clicks

        average_input_markup = self.total_cost / self.total_tt_cost

        expected_successes = int(self.total_clicks * 0.42)

        # Calculate total TT of successes
        if self.one_item_per_success:
            item_name = self.get_selected_item_name()
            if item_name in ALL_RESOURCES:
                item_tt_value = ALL_RESOURCES[item_name]
            else:
                item_tt_value = self.max_tt
            actual_item_tt = expected_successes * item_tt_value
            extra_residues = (self.total_tt_cost * Decimal("0.5")) - actual_item_tt
        else:
            actual_item_tt = (self.total_tt_cost * Decimal("0.5"))
            extra_residues = Decimal("0.0")

        residue_costs = Decimal("0.0")
        required_residue = Decimal("0.0")
        if self.use_residue:
            required_residue = (self.max_tt * expected_successes) - (self.total_tt_cost * Decimal("0.5"))
            residue_costs = required_residue * self.residue_markup
            self.residue_required_text.setText("{:.2f} PED".format(required_residue))
            actual_item_tt = self.max_tt * expected_successes


        self.total_cost += self.total_clicks * Decimal("0.01") * MarkupSingleton.get_markup_for_item(self.selected_blueprint).value
        self.total_tt_cost_text.setText("%.2f" % (self.total_tt_cost + required_residue) + " PED")
        self.total_cost_text.setText("%.2f" % (self.total_cost + residue_costs) + " PED")

        # Set Calculated Totals
        item = self.get_selected_item_name()

        self.exepcted_successes.setText(str(expected_successes))
        self.tt_as_final_item.setText("%.2f" % (actual_item_tt) + " PED")

        near_success_tt = (self.total_tt_cost * Decimal("0.45"))
        near_success_markup = (Decimal("0.4") * near_success_tt * average_input_markup) + (Decimal("0.6") * near_success_tt)

        self.expected_near_success_text.setText("%.2f" % (near_success_tt + extra_residues) + " PED")

        mu = MarkupSingleton.get_markup_for_item(item)
        if mu.is_absolute:
            expected = actual_item_tt + near_success_markup + Decimal(expected_successes * mu.value)
        else:
            expected = (actual_item_tt * mu.value) + near_success_markup + extra_residues
        self.expected_return.setText("%.2f" % expected + " PED")

        delta = (self.total_cost + residue_costs) - (near_success_markup + extra_residues)

        if mu.is_absolute:
            try:
                required_markup = (delta - (self.total_tt_cost * Decimal("0.5"))) / int(self.total_clicks * 0.42)
            except:
                required_markup = Decimal("0.00")
            self.minimum_markup.setText("+{:.2f}".format(required_markup))
        else:
            required_markup = delta / (actual_item_tt) * 100
            self.minimum_markup.setText("{:.3f}%".format(required_markup))

    def format_resources_from_selection(self):
        data = {"Resource": [], "Per Click": [], "Total": [], "TT Cost": [], "Markup": [], "Total Cost": []}
        for slot in ALL_BLUEPRINTS[self.selected_blueprint].slots:
            data["Resource"].append(slot.name)
            data["Per Click"].append(slot.count)
            data["Total"].append(slot.count * self.total_clicks)
            data["TT Cost"].append("%.3f" % (slot.count * self.total_clicks * ALL_RESOURCES[slot.name]))
            data["Markup"].append(MarkupSingleton.get_formatted_markup(slot.name))
            data["Total Cost"].append("%.3f" % MarkupSingleton.apply_markup_to_item(slot.name,
                                                                                    slot.count * self.total_clicks,
                                                                                    slot.count * self.total_clicks * ALL_RESOURCES[slot.name]))
        return data

    def on_blueprint_changed(self):
        self.selected_blueprint = self.bp_option.currentText()
        self.blueprint_table.clear()
        self.blueprint_table.setData(self.format_resources_from_selection())
        self.blueprint_markup_text.setText(MarkupSingleton.get_formatted_markup(self.selected_blueprint))

        # Set Calculated Totals
        item = self.get_selected_item_name()

        if not item:
            return
        self.item_markup.setText(MarkupSingleton.get_formatted_markup(item))

        self.calculate_crafting_totals()

    def on_bluprint_table_selected(self):
        indexes = self.blueprint_table.selectionModel().selectedRows()
        if not indexes:
            return
        self.blueprint_table_selected_row = [i.row() for i in indexes][0]

    def on_blueprint_table_changed(self):
        if self.blueprint_table_selected_row is None or self.blueprint_table is None:
            return
        name_cell = self.blueprint_table.item(self.blueprint_table_selected_row, 0)
        markup_cell = self.blueprint_table.item(self.blueprint_table_selected_row, 4)
        MarkupSingleton.add_markup_for_item(name_cell.text(), markup_cell.text())
        self.calculate_crafting_totals()
        self.blueprint_table.clearSelection()

