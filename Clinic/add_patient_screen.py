import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QScrollArea,
    QFrame,
    QStackedWidget,
    QScroller,
    QSizePolicy,
    QListWidget,
    QListWidgetItem
)
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt, QDate, QTimer

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


def load_env_files_for_patient_kiosk():
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
    load_env_files_for_patient_kiosk()

    token = None
    base_id = None

    if config is not None:
        token = getattr(config, "AIRTABLE_TOKEN", None)
        base_id = getattr(config, "BASE_ID", None)

    token = token or os.getenv("AIRTABLE_TOKEN") or os.getenv("AIRTABLE_API_KEY")
    base_id = base_id or os.getenv("BASE_ID") or os.getenv("AIRTABLE_BASE_ID")

    return token, base_id


class AddPatientScreen(QWidget):
    """Screen for adding a new patient to Airtable."""

    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.api = None
        self.patients_table = None
        self.last_print_data = None
        self.last_patient_id = ""
        self.init_airtable()
        self.init_ui()

    def init_airtable(self):
        if Api is None:
            print("AddPatientScreen: pyairtable is not available.")
            return

        token, base_id = get_airtable_settings()

        if not token or not base_id:
            print("AddPatientScreen: missing Airtable settings.")
            print("AddPatientScreen: token length = {}".format(len(token) if token else 0))
            print("AddPatientScreen: base id = {}".format(base_id))
            self.patients_table = None
            return

        try:
            self.api = Api(token)
            self.patients_table = self.api.table(base_id, TABLE_NAME)
            print("AddPatientScreen: Airtable connection ready. Base ID: {}".format(base_id))
        except Exception as e:
            print("AddPatientScreen: Airtable connection failed: {}".format(e))
            self.patients_table = None

    def init_ui(self):
        self.setStyleSheet("background-color: #F8FAFC;")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        self.btn_back_top = QPushButton("Back")
        self.btn_back_top.setFixedSize(75, 36)
        self.btn_back_top.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_back_top.clicked.connect(self.go_back)
        self.btn_back_top.setStyleSheet(self.secondary_button_style())

        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        title = QLabel("Add New Patient")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-family: 'Segoe UI'; font-size: 22px; font-weight: bold; color: #0F172A;")

        subtitle = QLabel("Fill in the details, then save or save and print a card.")
        subtitle.setAlignment(Qt.AlignLeft)
        subtitle.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: #64748B;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.btn_save = QPushButton("Save")
        self.btn_save.setFixedSize(95, 38)
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.clicked.connect(lambda: self.save_patient(print_after_save=False))
        self.btn_save.setStyleSheet(self.primary_button_style())

        self.btn_save_print = QPushButton("Save + Print")
        self.btn_save_print.setFixedSize(130, 38)
        self.btn_save_print.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save_print.clicked.connect(lambda: self.save_patient(print_after_save=True))
        self.btn_save_print.setStyleSheet(self.primary_button_style())

        self.btn_print_last = QPushButton("Print Last")
        self.btn_print_last.setFixedSize(105, 38)
        self.btn_print_last.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_print_last.clicked.connect(self.print_last_card)
        self.btn_print_last.setEnabled(False)
        self.btn_print_last.setStyleSheet(self.secondary_button_style())

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedSize(75, 38)
        self.btn_clear.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_clear.clicked.connect(self.clear_form)
        self.btn_clear.setStyleSheet(self.secondary_button_style())

        header.addWidget(self.btn_back_top)
        header.addLayout(title_box, stretch=1)
        header.addWidget(self.btn_save)
        header.addWidget(self.btn_save_print)
        header.addWidget(self.btn_print_last)
        header.addWidget(self.btn_clear)
        root.addLayout(header)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(30)
        self.status_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px; font-weight: bold;")
        root.addWidget(self.status_label)

        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QFrame.NoFrame)
        self.page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_scroll.verticalScrollBar().setSingleStep(28)
        self.page_scroll.verticalScrollBar().setPageStep(170)
        self.page_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        try:
            QScroller.grabGesture(self.page_scroll.viewport(), QScroller.LeftMouseButtonGesture)
        except Exception:
            pass
        self.page_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F8FAFC;
            }
            QScrollBar:vertical {
                background: #E2E8F0;
                width: 22px;
                margin: 0px;
                border-radius: 10px;
            }
            QScrollBar::handle:vertical {
                background: #64748B;
                min-height: 48px;
                border-radius: 10px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 8, 260)
        page_layout.setSpacing(8)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
        """)
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setHorizontalSpacing(14)
        card_layout.setVerticalSpacing(8)

        self.name_input = self.make_line_edit("Full name")
        self.language_list = self.make_multi_select_list(["Arabic", "Hebrew", "English", "Russian", "Tigrinya", "Amharic", "Ukrainian"])
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDisplayFormat("yyyy-MM-dd")
        self.dob_input.setDate(QDate.currentDate())

        self.dob_input.setMaximumDate(QDate.currentDate())  # מונע בחירת תאריך עתידי מהיום והלאה
        self.dob_input.setMinimumDate(QDate.currentDate().addYears(-120))

        self.dob_input.setStyleSheet(self.input_style())
        self.dob_input.setFixedHeight(38)

        calendar = self.dob_input.calendarWidget()
        calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #F1F5F9;
            }
            QCalendarWidget QToolButton {
                background-color: transparent;
                color: #0F172A;
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 6px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #E2E8F0;
                border-radius: 6px;
            }
            QCalendarWidget QSpinBox {
                background-color: #FFFFFF;
                color: #0F172A;
                selection-background-color: #4F46E5;
                selection-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 3px;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #FFFFFF;
                color: #0F172A;
                selection-background-color: #4F46E5;
                selection-color: #FFFFFF;
                outline: none;
            }
        """)

        self.phone_input = self.make_line_edit("Phone number")
        self.gender_combo = self.make_combo(["", "Female", "Male", "Non-binary"])
        self.emergency_input = self.make_line_edit("Emergency contact")
        self.city_input = self.make_line_edit("City / Unhoused")
        self.referred_input = self.make_line_edit("Referred by")
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes")
        self.notes_input.setFixedHeight(66)
        self.notes_input.setStyleSheet(self.input_style())

        self.manual_id_input = self.make_line_edit("Manual ID (Leave empty for auto)")

        self.add_field(card_layout, 0, 0, "Name", self.name_input)
        self.add_field(card_layout, 0, 1, "Language", self.language_list)
        self.add_field(card_layout, 1, 0, "Date of Birth", self.dob_input)
        self.add_field(card_layout, 1, 1, "Phone", self.phone_input)
        self.add_field(card_layout, 2, 0, "Gender", self.gender_combo)
        self.add_field(card_layout, 2, 1, "Emergy contact", self.emergency_input)
        self.add_field(card_layout, 3, 0, "City / Unhoused", self.city_input)
        self.add_field(card_layout, 3, 1, "Referred by", self.referred_input)
        self.add_field(card_layout, 4, 0, "Notes", self.notes_input)
        self.add_field(card_layout, 4, 1, "Manual ID", self.manual_id_input)

        page_layout.addWidget(card)

        bottom_hint = QLabel("Use the buttons at the top of the screen to save, print, clear, or go back.")
        bottom_hint.setAlignment(Qt.AlignCenter)
        bottom_hint.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; color: #64748B;")
        page_layout.addWidget(bottom_hint)

        self.page_scroll.setWidget(page)
        root.addWidget(self.page_scroll, stretch=1)

    def add_field(self, grid, row, column, label_text, widget):
        box = QVBoxLayout()
        box.setSpacing(3)
        label = QLabel(label_text)
        label.setStyleSheet("font-family: 'Segoe UI'; font-size: 11px; font-weight: bold; color: #334155;")
        box.addWidget(label)
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

    def make_multi_select_list(self, values):
        list_widget = QListWidget()
        list_widget.setFixedHeight(80)  # גובה שמאפשר לראות כמה שפות
        list_widget.setStyleSheet(self.input_style())
        for val in values:
            item = QListWidgetItem(val)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            list_widget.addItem(item)
        return list_widget

    def input_style(self):
        return """
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 9px;
                padding: 5px;
                font-family: 'Segoe UI';
                font-size: 13px;
                color: #334155;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #4F46E5;
            }
        """

    def primary_button_style(self):
        return """
            QPushButton {
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4338CA; }
            QPushButton:pressed { background-color: #3730A3; }
            QPushButton:disabled { background-color: #94A3B8; }
        """

    def secondary_button_style(self):
        return """
            QPushButton {
                background-color: #F8FAFC;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 9px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E2E8F0; }
            QPushButton:disabled { color: #94A3B8; border-color: #E2E8F0; }
        """

    def prepare_for_add(self):
        self.status_label.setText("")
        try:
            self.page_scroll.verticalScrollBar().setValue(0)
        except Exception:
            pass
        QTimer.singleShot(100, self.name_input.setFocus)

    def clear_form(self):
        self.name_input.clear()
        for i in range(self.language_list.count()):
            self.language_list.item(i).setCheckState(Qt.Unchecked)
        self.dob_input.setDate(QDate.currentDate())
        self.phone_input.clear()
        self.gender_combo.setCurrentIndex(0)
        self.emergency_input.clear()
        self.city_input.clear()
        self.referred_input.clear()
        self.notes_input.clear()
        self.manual_id_input.clear()
        self.status_label.setText("")
        self.name_input.setFocus()

    def collect_payload(self):
        payload = {}

        name = self.name_input.text().strip()
        if name:
            payload["Name"] = name

        selected_languages = []
        for i in range(self.language_list.count()):
            item = self.language_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_languages.append(item.text().strip())

        if selected_languages:
            payload["Language"] = selected_languages

        gender = self.gender_combo.currentText().strip()
        if gender:
            payload["Gender"] = gender

        payload["ID Type"] = "new"

        payload["Date of Birth"] = self.dob_input.date().toString("yyyy-MM-dd")

        phone = self.phone_input.text().strip()
        if phone:
            payload["Phone"] = phone

        emergency = self.emergency_input.text().strip()
        if emergency:
            payload["Emergy contact"] = emergency

        city = self.city_input.text().strip()
        if city:
            payload["City \\ Unhoused"] = city

        referred = self.referred_input.text().strip()
        if referred:
            payload["Referred by"] = referred

        notes = self.notes_input.toPlainText().strip()
        if notes:
            payload["Notes"] = notes

        manual_id = self.manual_id_input.text().strip()
        if manual_id:
            payload["Manual ID"] = manual_id

        return payload

    def _try_create_patient_record(self, payload):
        return self.patients_table.create(payload)

    def save_patient(self, print_after_save=False):
        if self.patients_table is None:
            self.show_status("Airtable settings are missing or not loaded.", success=False)
            return

        name = self.name_input.text().strip()
        if not name:
            self.show_status("Name is required.", success=False)
            self.name_input.setFocus()
            return

        payload = self.collect_payload()

        try:
            created = self._try_create_patient_record(payload)
            created = self.refresh_created_record(created)
            fields = created.get("fields", {}) if isinstance(created, dict) else {}
            personal_id = self.extract_personal_id(fields)

            self.last_patient_id = personal_id
            self.last_print_data = self.build_print_data(fields, payload, personal_id)
            self.btn_print_last.setEnabled(bool(self.last_print_data))

            msg = "Patient saved"
            if personal_id:
                msg += ". ID: {}".format(personal_id)
            else:
                msg += ". Patient ID is empty."

            if print_after_save:
                print_ok, print_message = self.print_card_data(self.last_print_data)
                if print_ok:
                    msg += ". Card sent to printer."
                else:
                    msg += " {}".format(print_message)

            self.show_status(msg, success=True)
            self.clear_form_keep_status()
        except Exception as e:
            print("AddPatientScreen: save failed: {}".format(e))
            self.show_status("Could not save patient. Check Airtable field values.", success=False)

    def refresh_created_record(self, created):
        if not isinstance(created, dict):
            return created
        record_id = created.get("id")
        if not record_id or self.patients_table is None:
            return created
        try:
            fresh = self.patients_table.get(record_id)
            if isinstance(fresh, dict):
                return fresh
        except Exception as e:
            print("AddPatientScreen: could not refresh created record: {}".format(e))
        return created

    def extract_personal_id(self, fields):
        value = fields.get("Personal ID", "") if isinstance(fields, dict) else ""
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value).strip()

    def split_patient_name(self, full_name):
        full_name = str(full_name or "").strip()
        if not full_name:
            return "Patient", ""
        parts = full_name.split(None, 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    def build_print_data(self, fields, payload, personal_id):
        if not personal_id:
            return None
        name = ""
        if isinstance(fields, dict):
            name = fields.get("Name", "")
        if not name:
            name = payload.get("Name", "")
        first_name, last_name = self.split_patient_name(name)
        return {
            "first": first_name,
            "last": last_name,
            "id": personal_id,
        }

    def print_last_card(self):
        ok, message = self.print_card_data(self.last_print_data)
        self.show_status(message, success=ok)

    def print_card_data(self, label_data):
        if create_label is None or print_label is None:
            print("AddPatientScreen: printer_engine is not available.")
            return False, "Printer module is not available."

        if not label_data or not label_data.get("id"):
            print("AddPatientScreen: no patient card data available for printing.")
            return False, "No saved patient card is available for printing."

        try:
            label_path = str(Path(__file__).resolve().parent / "last_patient_label.png")
            created_label = create_label(label_data, label_path)
            print_label(created_label)
            print("AddPatientScreen: patient card sent to printer for ID {}".format(label_data.get("id")))
            return True, "Card sent to printer."
        except Exception as e:
            print("AddPatientScreen: print failed: {}".format(e))
            return False, "Patient saved, but card printing failed."

    def clear_form_keep_status(self):
        msg = self.status_label.text()
        style = self.status_label.styleSheet()
        self.clear_form()
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(style)

    def show_status(self, text, success=True):
        color = "#10B981" if success else "#EF4444"
        self.status_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px; font-weight: bold; color: {};".format(color))
        self.status_label.setText(text)

    def go_back(self):
        if self.stack is not None:
            self.stack.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    stack = QStackedWidget()
    screen = AddPatientScreen(stack)
    stack.addWidget(screen)
    stack.setCurrentIndex(0)
    screen.prepare_for_add()
    stack.resize(800, 480)
    stack.show()
    sys.exit(app.exec_())
