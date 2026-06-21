from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from pyairtable import Api
from datetime import datetime  # <--- הוספנו את ייבוא התאריך והשעה

import printer_engine  # Your existing printer logic
import config  # Import your central configuration

TABLE_NAME = "Patients"


class NewPatientScreen(QWidget):
    """ Screen for registering new patients and printing their ID labels """

    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.image_path = 'label.png'

        # Initialize Airtable connection using config file
        try:
            self.api = Api(config.AIRTABLE_TOKEN)
            self.patients_table = self.api.table(config.BASE_ID, TABLE_NAME)
        except Exception as e:
            print(f"Airtable Connection Error: {e}")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Register New Patient")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addSpacing(30)

        # Input fields
        self.first_input = QLineEdit()
        self.first_input.setPlaceholderText("First Name")
        self.first_input.setFixedSize(300, 40)

        self.last_input = QLineEdit()
        self.last_input.setPlaceholderText("Last Name")
        self.last_input.setFixedSize(300, 40)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID Number")
        self.id_input.setFixedSize(300, 40)

        layout.addWidget(self.first_input, alignment=Qt.AlignCenter)
        layout.addWidget(self.last_input, alignment=Qt.AlignCenter)
        layout.addWidget(self.id_input, alignment=Qt.AlignCenter)
        layout.addSpacing(40)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        btn_back = QPushButton("Back to Menu")
        btn_back.setFixedSize(200, 50)
        btn_back.clicked.connect(self.go_back)

        self.generate_btn = QPushButton("Save & Print ID")
        self.generate_btn.setFixedSize(200, 50)
        self.generate_btn.clicked.connect(self.register_and_print)

        btn_layout.addWidget(btn_back)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.generate_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def go_back(self):
        # Clear fields when going back
        self.first_input.clear()
        self.last_input.clear()
        self.id_input.clear()
        self.stack.setCurrentIndex(0)

    def register_and_print(self):
        first = self.first_input.text().strip()
        last = self.last_input.text().strip()
        tz_id = self.id_input.text().strip()

        if not first or not last or not tz_id:
            QMessageBox.warning(self, "Error", "Please fill all fields!")
            return

        # Generate unique patient ID
        patient_id = f"PAT-{tz_id}"
        full_name = f"{first} {last}"

        # שמירת התאריך והשעה הנוכחיים בפורמט ISO
        creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


        # Save to Airtable
        try:
            self.patients_table.create({
                "Patient_ID": patient_id,
                "Full_Name": full_name,
                "Date Created": creation_time  # <--- הוספת השדה החדש
            })
        except Exception as e:
            QMessageBox.critical(self, "Cloud Error", f"Failed to save to Airtable:\n{e}")
            return

        # Prepare data for the printer engine
        data_to_print = {
            'first': first,
            'last': last,
            'id': patient_id
        }

        # Trigger printing process
        printer_engine.create_label(data_to_print, self.image_path)
        printer_engine.print_label(self.image_path)

        QMessageBox.information(self, "Success", "Patient registered and label printed successfully!")
        self.go_back()