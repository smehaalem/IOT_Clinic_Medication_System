from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from pyairtable import Api
from pyairtable.formulas import match
import json
import config  # Import your central configuration

TABLE_NAME = "Patients"


class CheckinScreen(QWidget):
    """ Screen for handling returning patients via barcode scanning """

    def __init__(self, stack):
        super().__init__()
        self.stack = stack

        # Initialize Airtable connection using config file
        try:
            print(
                f"DEBUG: Attempting connection with TOKEN len: {len(config.AIRTABLE_TOKEN) if config.AIRTABLE_TOKEN else 0}")
            print(f"DEBUG: Using BASE_ID: {config.BASE_ID}")
            self.api = Api(config.AIRTABLE_TOKEN)
            self.patients_table = self.api.table(config.BASE_ID, TABLE_NAME)
            print("DEBUG: Connection success!")
        except Exception as e:
            print(f"DEBUG: Connection failed with error: {e}")
            # נשאיר את ההודעה למשתמש גם במסך עצמו כדי שנראה
            # (אבל נשאיר את ההדפסה בטרמינל כדי לאבחן)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Returning Patient")
        title.setFont(QFont("Arial", 30, QFont.Bold))

        subtitle = QLabel("Please scan the QR code on the patient's card...")
        subtitle.setFont(QFont("Arial", 18))

        # Hidden/Focused input specifically for the barcode scanner
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Waiting for scanner...")
        self.scan_input.setFixedSize(300, 50)
        self.scan_input.setFont(QFont("Arial", 16))
        self.scan_input.setAlignment(Qt.AlignCenter)

        # Connect the Enter key event (scanner suffix) to the handler function
        self.scan_input.returnPressed.connect(self.handle_scan)

        self.welcome_msg = QLabel("")
        self.welcome_msg.setFont(QFont("Arial", 22))
        self.welcome_msg.setAlignment(Qt.AlignCenter)

        btn_back = QPushButton("Back to Menu")
        btn_back.setFixedSize(200, 50)
        btn_back.clicked.connect(self.go_back)

        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.scan_input, alignment=Qt.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.welcome_msg, alignment=Qt.AlignCenter)
        layout.addSpacing(50)
        layout.addWidget(btn_back, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def prepare_for_scan(self):
        """ Resets UI and puts focus on the input field ready for hardware scanner """
        self.scan_input.clear()
        self.welcome_msg.setText("")
        self.scan_input.setFocus()

    def go_back(self):
        self.stack.setCurrentIndex(0)

    def handle_scan(self):
        """ Triggered automatically when the barcode scanner finishes reading """
        scanned_text = self.scan_input.text().strip()
        if not scanned_text:
            return

        # Clear input for the next potential scan
        self.scan_input.clear()

        # ==========================================
        # חילוץ ה-ID מתוך ה-QR (JSON) שהסורק קרא
        # ==========================================
        try:
            # מנסה לפענח את הטקסט כמילון JSON
            parsed_data = json.loads(scanned_text)
            scanned_id = parsed_data.get('id', scanned_text)
        except json.JSONDecodeError:
            # אם משום מה נסרק ברקוד רגיל (לא JSON), נשתמש בו כמו שהוא
            scanned_id = scanned_text
        # ==========================================

        try:
            # 1. Search for patient ID in Airtable (עכשיו מחפשים רק PAT-12345)
            formula = match({"Patient_ID": scanned_id})
            records = self.patients_table.all(formula=formula)

            if records:
                # 2. Patient found
                record_id = records[0]['id']
                patient_name = records[0]['fields'].get('Full_Name', 'Patient')

                # 3. Update 'Last_Visit_Date' to current timestamp (ISO format)
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.patients_table.update(record_id, {"Last Visit": now_str})

                # 4. Display personalized success message
                self.welcome_msg.setStyleSheet("color: green;")
                self.welcome_msg.setText(f"Welcome back, {patient_name}!\nYour visit has been logged.")
            else:
                # Patient not found
                self.welcome_msg.setStyleSheet("color: red;")
                self.welcome_msg.setText("Error: Patient ID not found in system.")

        except Exception as e:
            self.welcome_msg.setStyleSheet("color: red;")
            self.welcome_msg.setText("Connection error. Please try again.")

        # Return focus to input so the next card can be scanned immediately
        self.scan_input.setFocus()