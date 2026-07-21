# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QDateEdit,
    QScrollArea, QFrame, QStackedWidget, QScroller, QSizePolicy,
    QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QCursor

try:
    from pyairtable import Api
except Exception:
    Api = None

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    import config
except Exception:
    config = None

try:
    from printer_engine import create_label, print_label
except Exception:
    create_label = None
    print_label = None


TABLE_NAME = "Patients"


def load_env():
    if load_dotenv is None:
        return

    here = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / ".env",
        here / ".env",
        here.parent / ".env",
        here.parent / "medication_sys" / ".env",
        here.parent / "Clinic" / ".env",
    ]

    for env_path in candidates:
        try:
            if env_path.exists():
                load_dotenv(str(env_path), override=False)
        except Exception:
            pass


def get_airtable_settings():
    load_env()

    token = getattr(config, "AIRTABLE_TOKEN", None) if config else None
    base_id = getattr(config, "BASE_ID", None) if config else None

    token = token or os.getenv("AIRTABLE_TOKEN") or os.getenv("AIRTABLE_API_KEY")
    base_id = base_id or os.getenv("BASE_ID") or os.getenv("AIRTABLE_BASE_ID")

    return token, base_id


def escape_formula_text(value):
    return str(value or "").replace("\\", "\\\\").replace("'", "\\'")


class EditPatientScreen(QWidget):
    """
    Search by exact Personal ID or exact full name, then edit the same
    Airtable patient record.
    """

    def __init__(self, stack):
        super().__init__()

        self.stack = stack
        self.api = None
        self.patients_table = None
        self.current_record_id = None
        self.current_fields = {}

        self.internal_stack = QStackedWidget(self)

        self.init_airtable()
        self.init_search_page()
        self.init_edit_page()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

    def init_airtable(self):
        if Api is None:
            print("EditPatientScreen: pyairtable is unavailable.")
            return

        token, base_id = get_airtable_settings()

        if not token or not base_id:
            print("EditPatientScreen: missing Airtable settings.")
            return

        try:
            self.api = Api(token)
            self.patients_table = self.api.table(base_id, TABLE_NAME)
        except Exception as error:
            print(f"EditPatientScreen: connection failed: {error}")

    # -----------------------------------------------------------------
    # Search page
    # -----------------------------------------------------------------
    def init_search_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setFixedSize(75, 36)
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(self.secondary_button_style())
        back_btn.clicked.connect(self.go_back)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        title = QLabel("Edit Existing Patient")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #0F172A;"
        )

        subtitle = QLabel("Search by exact full name or exact Personal ID.")
        subtitle.setStyleSheet("font-size: 12px; color: #64748B;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addWidget(back_btn)
        header.addLayout(title_box, stretch=1)
        layout.addLayout(header)

        self.search_status = QLabel("")
        self.search_status.setAlignment(Qt.AlignCenter)
        self.search_status.setFixedHeight(34)
        layout.addWidget(self.search_status)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        card_layout.addWidget(self.make_label("Search by"))

        self.search_method = QComboBox()
        self.search_method.addItems(["Personal ID", "Full Name"])
        self.search_method.setFixedHeight(38)
        self.search_method.setStyleSheet(self.input_style())
        self.search_method.currentIndexChanged.connect(
            self.update_search_placeholder
        )
        card_layout.addWidget(self.search_method)

        card_layout.addWidget(self.make_label("Search value"))

        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(42)
        self.search_input.setStyleSheet(self.input_style())
        self.search_input.returnPressed.connect(self.search_patient)
        card_layout.addWidget(self.search_input)

        search_btn = QPushButton("Search Patient")
        search_btn.setMinimumHeight(42)
        search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        search_btn.setStyleSheet(self.primary_button_style())
        search_btn.clicked.connect(self.search_patient)
        card_layout.addWidget(search_btn)

        layout.addWidget(card)
        layout.addStretch()

        self.update_search_placeholder()
        self.internal_stack.addWidget(page)

    def update_search_placeholder(self):
        if self.search_method.currentText() == "Personal ID":
            self.search_input.setPlaceholderText("Enter exact Personal ID")
        else:
            self.search_input.setPlaceholderText(
                "Please enter exact full name"
            )

        self.search_input.clear()
        self.search_status.clear()
        QTimer.singleShot(50, self.search_input.setFocus)

    def search_patient(self):
        if self.patients_table is None:
            self.set_status(
                self.search_status,
                "Airtable settings are missing or not loaded.",
                False
            )
            return

        value = self.search_input.text().strip()

        if not value:
            self.set_status(
                self.search_status,
                "Please enter a search value.",
                False
            )
            return

        escaped = escape_formula_text(value)

        if self.search_method.currentText() == "Personal ID":
            formula = f"{{Personal ID}} = '{escaped}'"
        else:
            formula = (
                f"LOWER(TRIM({{Name}})) = "
                f"LOWER(TRIM('{escaped}'))"
            )

        try:
            records = self.patients_table.all(formula=formula)

            if not records:
                self.set_status(
                    self.search_status,
                    "No matching patient was found.",
                    False
                )
                return

            record = records[0]
            self.current_record_id = (
                record.id if hasattr(record, "id") else record.get("id")
            )
            self.current_fields = (
                dict(record.fields or {})
                if hasattr(record, "fields")
                else dict(record.get("fields", {}) or {})
            )

            self.load_patient(self.current_fields)
            self.internal_stack.setCurrentIndex(1)

        except Exception as error:
            print(f"EditPatientScreen: search failed: {error}")
            self.set_status(
                self.search_status,
                "Could not search for the patient.",
                False
            )

    # -----------------------------------------------------------------
    # Edit page
    # -----------------------------------------------------------------
    def init_edit_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        root = QVBoxLayout(page)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(6)

        header = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setFixedSize(75, 36)
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(self.secondary_button_style())
        back_btn.clicked.connect(self.back_to_search)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        title = QLabel("Edit Patient")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #0F172A;"
        )

        self.identity_label = QLabel("")
        self.identity_label.setStyleSheet("font-size: 12px; color: #64748B;")

        title_box.addWidget(title)
        title_box.addWidget(self.identity_label)

        save_btn = QPushButton("Save Changes")
        save_btn.setFixedSize(125, 38)
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))
        save_btn.setStyleSheet(self.primary_button_style())
        save_btn.clicked.connect(lambda: self.update_patient(False))

        save_print_btn = QPushButton("Save + Print")
        save_print_btn.setFixedSize(130, 38)
        save_print_btn.setCursor(QCursor(Qt.PointingHandCursor))
        save_print_btn.setStyleSheet(self.primary_button_style())
        save_print_btn.clicked.connect(lambda: self.update_patient(True))

        delete_btn = QPushButton("Delete Patient")
        delete_btn.setFixedSize(125, 38)
        delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        delete_btn.setStyleSheet(self.delete_button_style())
        delete_btn.clicked.connect(self.delete_patient)

        header.addWidget(back_btn)
        header.addLayout(title_box, stretch=1)
        header.addWidget(delete_btn)
        header.addWidget(save_btn)
        header.addWidget(save_print_btn)
        root.addLayout(header)

        self.edit_status = QLabel("")
        self.edit_status.setAlignment(Qt.AlignCenter)
        self.edit_status.setFixedHeight(30)
        root.addWidget(self.edit_status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.verticalScrollBar().setSingleStep(28)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        try:
            QScroller.grabGesture(
                self.scroll.viewport(),
                QScroller.LeftMouseButtonGesture
            )
        except Exception:
            pass

        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F8FAFC;
            }

            QScrollBar:vertical {
                background: #E2E8F0;
                width: 22px;
                border-radius: 10px;
            }

            QScrollBar::handle:vertical {
                background: #64748B;
                min-height: 48px;
                border-radius: 10px;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background-color: #F8FAFC;")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 260)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
        """)

        grid = QGridLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self.name_input = self.make_line_edit("Full name")
        self.language_list = self.make_language_list()
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDisplayFormat("yyyy-MM-dd")
        self.dob_input.setMaximumDate(QDate.currentDate())
        self.dob_input.setMinimumDate(QDate.currentDate().addYears(-120))
        self.dob_input.setFixedHeight(38)
        self.dob_input.setStyleSheet(self.input_style())

        self.phone_input = self.make_line_edit("Phone number")
        self.gender_combo = self.make_combo(["", "Female", "Male", "Non-binary"])
        self.id_type_combo = self.make_combo(["", "new", "old"])
        self.emergency_input = self.make_line_edit("Emergency contact")
        self.city_input = self.make_line_edit("City / Unhoused")
        self.referred_input = self.make_line_edit("Referred by")

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes")
        self.notes_input.setFixedHeight(66)
        self.notes_input.setStyleSheet(self.input_style())

        self.personal_id_input = self.make_line_edit("Personal ID")
        self.personal_id_input.setEnabled(False)

        self.manual_id_input = self.make_line_edit("Manual ID")
        self.manual_id_input.setEnabled(False)

        self.add_field(grid, 0, 0, "Name", self.name_input)
        self.add_field(grid, 0, 1, "Language", self.language_list)
        self.add_field(grid, 1, 0, "Date of Birth", self.dob_input)
        self.add_field(grid, 1, 1, "Phone", self.phone_input)
        self.add_field(grid, 2, 0, "Gender", self.gender_combo)
        self.add_field(grid, 2, 1, "ID Type", self.id_type_combo)
        self.add_field(grid, 3, 0, "Emergency contact", self.emergency_input)
        self.add_field(grid, 3, 1, "City / Unhoused", self.city_input)
        self.add_field(grid, 4, 0, "Referred by", self.referred_input)
        self.add_field(grid, 4, 1, "Notes", self.notes_input)
        self.add_field(grid, 5, 0, "Personal ID", self.personal_id_input)
        self.add_field(grid, 5, 1, "Manual ID", self.manual_id_input)

        content_layout.addWidget(card)
        self.scroll.setWidget(content)
        root.addWidget(self.scroll, stretch=1)

        self.internal_stack.addWidget(page)

    def load_patient(self, fields):
        self.name_input.setText(self.clean(fields.get("Name")))
        self.phone_input.setText(self.clean(fields.get("Phone")))
        self.emergency_input.setText(self.clean(fields.get("Emergy contact")))
        self.city_input.setText(self.clean(fields.get("City \\ Unhoused")))
        self.referred_input.setText(self.clean(fields.get("Referred by")))
        self.notes_input.setPlainText(self.clean(fields.get("Notes")))

        personal_id = self.clean(fields.get("Personal ID"))
        manual_id = self.clean(fields.get("Manual ID"))

        self.personal_id_input.setText(personal_id)
        self.manual_id_input.setText(manual_id)
        self.identity_label.setText(f"Patient ID: {personal_id or '-'}")

        self.set_combo(self.gender_combo, self.clean(fields.get("Gender")))
        self.set_combo(self.id_type_combo, self.clean(fields.get("ID Type")))

        dob = QDate.fromString(
            self.clean(fields.get("Date of Birth")),
            "yyyy-MM-dd"
        )
        self.dob_input.setDate(dob if dob.isValid() else QDate.currentDate())

        languages = fields.get("Language", [])
        if not isinstance(languages, list):
            languages = [languages] if languages else []

        selected = {str(value).strip().lower() for value in languages}

        for index in range(self.language_list.count()):
            item = self.language_list.item(index)
            item.setCheckState(
                Qt.Checked
                if item.text().strip().lower() in selected
                else Qt.Unchecked
            )

        self.edit_status.clear()
        self.scroll.verticalScrollBar().setValue(0)
        QTimer.singleShot(100, self.name_input.setFocus)

    def collect_payload(self):
        languages = []

        for index in range(self.language_list.count()):
            item = self.language_list.item(index)
            if item.checkState() == Qt.Checked:
                languages.append(item.text().strip())

        return {
            "Name": self.name_input.text().strip(),
            "Language": languages,
            "Gender": self.gender_combo.currentText().strip(),
            "ID Type": self.id_type_combo.currentText().strip(),
            "Date of Birth": self.dob_input.date().toString("yyyy-MM-dd"),
            "Phone": self.phone_input.text().strip(),
            "Emergy contact": self.emergency_input.text().strip(),
            "City \\ Unhoused": self.city_input.text().strip(),
            "Referred by": self.referred_input.text().strip(),
            "Notes": self.notes_input.toPlainText().strip(),
        }

    def update_patient(self, print_after_save=False):
        if not self.current_record_id:
            self.set_status(
                self.edit_status,
                "No patient record is selected.",
                False
            )
            return

        # Existing patient fields may intentionally be cleared.
        # Do not require the name or any other editable field during an update.
        payload = self.collect_payload()

        try:
            updated = self.patients_table.update(
                self.current_record_id,
                payload
            )
            fields = (
                updated.get("fields", {})
                if isinstance(updated, dict)
                else payload
            )

            message = "Patient updated successfully."

            if print_after_save:
                personal_id = self.clean(
                    fields.get("Personal ID")
                    or self.current_fields.get("Personal ID")
                )
                print_data = self.build_print_data(
                    fields,
                    payload,
                    personal_id
                )
                ok, print_message = self.print_card(print_data)
                message += (
                    " Card sent to printer."
                    if ok
                    else f" {print_message}"
                )

            self.current_fields.update(payload)
            self.set_status(self.edit_status, message, True)

        except Exception as error:
            print(f"EditPatientScreen: update failed: {error}")
            self.set_status(
                self.edit_status,
                "Could not update patient.",
                False
            )

    def delete_patient(self):
        """
        Permanently delete the currently loaded patient from Airtable.
        """
        if self.patients_table is None:
            self.set_status(
                self.edit_status,
                "Airtable settings are missing or not loaded.",
                False
            )
            return

        if not self.current_record_id:
            self.set_status(
                self.edit_status,
                "No patient record is selected.",
                False
            )
            return

        patient_name = self.name_input.text().strip() or "Unknown"
        personal_id = self.personal_id_input.text().strip() or "-"

        confirmation = QMessageBox.question(
            self,
            "Delete Patient",
            (
                "Are you sure you want to permanently delete this patient?\n\n"
                f"Name: {patient_name}\n"
                f"Personal ID: {personal_id}\n\n"
                "This action cannot be undone."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirmation != QMessageBox.Yes:
            return

        try:
            self.patients_table.delete(self.current_record_id)

            self.current_record_id = None
            self.current_fields = {}

            self.search_input.clear()
            self.internal_stack.setCurrentIndex(0)

            self.set_status(
                self.search_status,
                f"Patient '{patient_name}' was deleted successfully.",
                True
            )
            QTimer.singleShot(100, self.search_input.setFocus)

        except Exception as error:
            print(f"EditPatientScreen: delete failed: {error}")
            self.set_status(
                self.edit_status,
                "Could not delete the patient.",
                False
            )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def prepare_for_edit(self):
        self.current_record_id = None
        self.current_fields = {}
        self.search_input.clear()
        self.search_status.clear()
        self.internal_stack.setCurrentIndex(0)
        QTimer.singleShot(100, self.search_input.setFocus)

    def back_to_search(self):
        self.internal_stack.setCurrentIndex(0)
        QTimer.singleShot(100, self.search_input.setFocus)

    def go_back(self):
        if self.stack is not None:
            self.stack.setCurrentIndex(0)

    @staticmethod
    def clean(value):
        if value is None:
            return ""
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value).strip()

    @staticmethod
    def set_combo(combo, value):
        index = combo.findText(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    @staticmethod
    def set_status(label, text, success):
        color = "#10B981" if success else "#EF4444"
        label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {color};"
        )
        label.setText(text)

    @staticmethod
    def make_label(text):
        label = QLabel(text)
        label.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #334155;"
        )
        return label

    def add_field(self, grid, row, column, text, widget):
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(self.make_label(text))
        box.addWidget(widget)
        grid.addLayout(box, row, column)

    def make_line_edit(self, placeholder):
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setFixedHeight(38)
        field.setStyleSheet(self.input_style())
        return field

    def make_combo(self, values):
        combo = QComboBox()
        combo.addItems(values)
        combo.setFixedHeight(38)
        combo.setStyleSheet(self.input_style())
        return combo

    def make_language_list(self):
        widget = QListWidget()
        widget.setFixedHeight(80)
        widget.setStyleSheet(self.input_style())

        for value in [
            "Arabic", "Hebrew", "English", "Russian",
            "Tigrinya", "Amharic", "Ukrainian"
        ]:
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            widget.addItem(item)

        return widget

    @staticmethod
    def input_style():
        return """
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 9px;
                padding: 5px;
                font-size: 13px;
                color: #334155;
            }

            QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
            QDateEdit:focus, QListWidget:focus {
                border: 2px solid #4F46E5;
            }

            QLineEdit:disabled {
                background-color: #F1F5F9;
                color: #64748B;
            }
        """

    @staticmethod
    def primary_button_style():
        return """
            QPushButton {
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton:pressed {
                background-color: #3730A3;
            }
        """

    @staticmethod
    def delete_button_style():
        return """
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #B91C1C;
            }

            QPushButton:pressed {
                background-color: #991B1B;
            }
        """

    @staticmethod
    def secondary_button_style():
        return """
            QPushButton {
                background-color: #F8FAFC;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 9px;
                font-size: 12px;
                font-weight: bold;
            }
        """

    @staticmethod
    def split_name(full_name):
        parts = str(full_name or "").strip().split(None, 1)
        if not parts:
            return "Patient", ""
        return parts[0], parts[1] if len(parts) > 1 else ""

    def build_print_data(self, fields, payload, personal_id):
        if not personal_id:
            return None

        name = self.clean(fields.get("Name")) or payload.get("Name", "")
        first, last = self.split_name(name)

        return {"first": first, "last": last, "id": personal_id}

    def print_card(self, data):
        if create_label is None or print_label is None:
            return False, "Printer module is not available."

        if not data or not data.get("id"):
            return False, "No patient ID is available for printing."

        try:
            path = str(
                Path(__file__).resolve().parent
                / "last_edited_patient_label.png"
            )
            print_label(create_label(data, path))
            return True, "Card sent to printer."
        except Exception as error:
            print(f"EditPatientScreen: print failed: {error}")
            return False, "Patient updated, but printing failed."


if __name__ == "__main__":
    app = QApplication(sys.argv)

    stack = QStackedWidget()
    screen = EditPatientScreen(stack)

    stack.addWidget(screen)
    stack.resize(800, 480)
    stack.show()

    screen.prepare_for_edit()

    sys.exit(app.exec_())
