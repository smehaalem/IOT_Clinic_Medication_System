from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtGui import QFont, QCursor
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

        self.init_ui()

    def init_ui(self):
        # Apply modern background color to match the dashboard style
        self.setStyleSheet("background-color: #F8FAFC;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Title styling
        title = QLabel("Returning Patient")
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 32px;
                font-weight: bold;
                color: #0F172A;
                margin-bottom: 8px;
            }
        """)

        # Subtitle styling providing clear instruction
        subtitle = QLabel("Please scan the QR code on the patient's card...")
        subtitle.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 16px;
                color: #64748B;
                margin-bottom: 25px;
            }
        """)

        # Focused input specifically styled for the barcode scanner hardware interaction
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Waiting for scanner...")
        self.scan_input.setFixedSize(340, 50)
        self.scan_input.setAlignment(Qt.AlignCenter)
        self.scan_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
                padding: 8px;
                font-family: 'Segoe UI';
                font-size: 16px;
                color: #334155;
            }
            QLineEdit:focus {
                border: 2px solid #4F46E5;
            }
        """)

        # Connect the Enter key event (scanner suffix) to the handler function
        self.scan_input.returnPressed.connect(self.handle_scan)

        # Welcome message label placeholder with generic initial properties
        self.welcome_msg = QLabel("")
        self.welcome_msg.setAlignment(Qt.AlignCenter)
        self.welcome_msg.setStyleSheet("font-family: 'Segoe UI'; font-size: 18px; font-weight: bold;")

        # Return button styled as a clean text-link to keep structural hierarchy
        btn_back = QPushButton("⬅️ Back to Menu")
        btn_back.setFixedSize(160, 45)
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748B;
                border: none;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 14px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #475569;
            }
        """)
        btn_back.clicked.connect(self.go_back)

        # Assemble layout
        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignCenter)
        layout.addWidget(self.scan_input, alignment=Qt.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.welcome_msg, alignment=Qt.AlignCenter)
        layout.addSpacing(40)
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
        # Extract ID from the QR (JSON) read by the hardware scanner
        # ==========================================
        try:
            # Attempt to parse scanned text as a JSON dictionary
            parsed_data = json.loads(scanned_text)
            scanned_id = parsed_data.get('id', scanned_text)
        except json.JSONDecodeError:
            # Fallback if a plain barcode text format is processed instead of structural JSON
            scanned_id = scanned_text
        # ==========================================

        try:
            # 1. Search for patient ID in Airtable
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
                self.welcome_msg.setStyleSheet(
                    "font-family: 'Segoe UI'; font-size: 18px; font-weight: bold; color: #10B981;")
                self.welcome_msg.setText(f"🎉 Welcome back, {patient_name}!\nYour visit has been logged.")
            else:
                # Patient not found
                self.welcome_msg.setStyleSheet(
                    "font-family: 'Segoe UI'; font-size: 16px; font-weight: bold; color: #EF4444;")
                self.welcome_msg.setText("❌ Error: Patient ID not found in system.")

        except Exception as e:
            self.welcome_msg.setStyleSheet(
                "font-family: 'Segoe UI'; font-size: 16px; font-weight: bold; color: #EF4444;")
            self.welcome_msg.setText("⚠️ Connection error. Please try again.")

        # Return focus to input so the next card can be scanned immediately
        self.scan_input.setFocus()