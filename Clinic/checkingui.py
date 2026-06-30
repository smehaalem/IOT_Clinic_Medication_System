import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
import airtable_api


class CheckinScreen(QWidget):
    """
    Highly readable Patient Check-In Terminal.
    ⚠️ Updated: Fully matches Airtable columns 'Patient_ID' and 'Full_Name'.
    """

    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.init_ui()

    def init_ui(self):
        # Establish white canvas theme with modern large font sizing
        self.setStyleSheet("background-color: #FFFFFF; border: none; font-family: 'Segoe UI';")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)
        main_layout.setAlignment(Qt.AlignCenter)

        # Centered spacious form card container
        form_card = QFrame()
        form_card.setFixedWidth(580)
        form_card.setStyleSheet("background-color: #FFFFFF; border: 2px solid #E2E8F0; border-radius: 20px;")

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(18)

        # Bold prominent main title
        header_title = QLabel("Patient Check-In")
        header_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #4F46E5; border: none;")
        form_layout.addWidget(header_title)

        # Simplified prominent sub-header instructions
        desc_text = QLabel("Please enter your name and ID number to get your QR ticket:")
        desc_text.setStyleSheet("font-size: 16px; color: #475569; border: none; margin-bottom: 5px;")
        form_layout.addWidget(desc_text)

        # Input Section 1: Full Name
        form_layout.addWidget(
            QLabel("Your Full Name:", styleSheet="font-size: 14px; font-weight: bold; color: #1E293B; border: none;"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Type your full name here...")
        self.name_input.setStyleSheet(self.get_large_input_style())
        form_layout.addWidget(self.name_input)

        # Input Section 2: ID Number
        form_layout.addWidget(QLabel("Your ID Card Number:",
                                     styleSheet="font-size: 14px; font-weight: bold; color: #1E293B; border: none;"))
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Type your ID number here...")
        self.id_input.setStyleSheet(self.get_large_input_style())
        form_layout.addWidget(self.id_input)

        form_layout.addSpacing(15)

        # Action Buttons Layout Matrix
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        back_btn = QPushButton("⬅️ Back")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setMinimumHeight(55)
        back_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #475569; font-weight: bold; font-size: 16px; border: 1px solid #E2E8F0; border-radius: 12px; }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        self.verify_btn = QPushButton("Confirm & Print Ticket")
        self.verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.verify_btn.setMinimumHeight(55)
        self.verify_btn.setStyleSheet("""
            QPushButton { background-color: #4F46E5; color: white; font-weight: bold; font-size: 16px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #4338CA; }
        """)
        self.verify_btn.clicked.connect(self.process_patient_kiosk_check)

        btn_layout.addWidget(back_btn, stretch=1)
        btn_layout.addWidget(self.verify_btn, stretch=2)
        form_layout.addLayout(btn_layout)

        main_layout.addWidget(form_card, alignment=Qt.AlignCenter)

    def prepare_for_scan(self):
        """ Clears fields on entrance view refresh """
        self.name_input.clear()
        self.id_input.clear()
        self.name_input.setFocus()

    def process_patient_kiosk_check(self):
        """ Secure query lookup mapping entries to Airtable 'Patient_ID' and 'Full_Name' keys """
        entered_name = self.name_input.text().strip()
        entered_id = self.id_input.text().strip()

        if not entered_name or not entered_id:
            msg_box = QMessageBox(QMessageBox.Warning, "Warning", "Please type both your Name and ID number.",
                                  parent=self)
            msg_box.setStyleSheet("QLabel { font-size: 15px; } QPushButton { font-size: 14px; padding: 6px 14px; }")
            msg_box.exec_()
            return

        try:
            if not hasattr(airtable_api, 'airtable_api') or airtable_api.airtable_api is None:
                msg_box = QMessageBox(QMessageBox.Critical, "Error",
                                      "System offline. Please report this to clinic staff.", parent=self)
                msg_box.setStyleSheet("QLabel { font-size: 15px; }")
                msg_box.exec_()
                return

            patients_table = airtable_api.airtable_api.table(airtable_api.config.BASE_ID, "Patients")

            # 🔥 Fix: Formula strictly maps keys containing underscores as shown in Airtable snapshot
            formula = f"AND({{Patient_ID}} = '{entered_id}', LOWER({{Full_Name}}) = LOWER('{entered_name}'))"
            records = patients_table.all(formula=formula)

            if records:
                # Flow A: Verified account match dialog with extra large clean readable text
                success_box = QMessageBox(self)
                success_box.setIcon(QMessageBox.Information)
                success_box.setWindowTitle("Check-In Complete")
                success_box.setText(
                    f"Welcome, {entered_name}!\n\nYour profile verification is successful.\nYour personal QR ticket code is now printing...")
                success_box.setStyleSheet(
                    "QLabel { font-size: 16px; font-weight: bold; color: #1E293B; line-height: 22px; } QPushButton { font-size: 14px; padding: 6px 16px; }")
                success_box.exec_()

                self.stack.setCurrentIndex(0)
            else:
                # Flow B: Reroute message notice with extra large clear instructions
                fail_box = QMessageBox(self)
                fail_box.setIcon(QMessageBox.Critical)
                fail_box.setWindowTitle("Not Registered")
                fail_box.setText(
                    "We cannot find your profile in our clinic system.\n\n"
                    "Please proceed to the Medical Secretary desk (המזכירות).\n"
                    "The registration staff will sign you up immediately."
                )
                fail_box.setStyleSheet(
                    "QLabel { font-size: 16px; font-weight: bold; color: #991B1B; line-height: 22px; } QPushButton { font-size: 14px; padding: 6px 16px; }")
                fail_box.exec_()
                self.id_input.clear()

        except Exception as e:
            err_box = QMessageBox(QMessageBox.Critical, "Error",
                                  "Connection failed. Please try again or ask for assistance.", parent=self)
            err_box.setStyleSheet("QLabel { font-size: 15px; }")
            err_box.exec_()

    def get_large_input_style(self):
        return """
            QLineEdit {
                padding: 12px; border: 2px solid #CBD5E1; border-radius: 10px; font-size: 16px; 
                background-color: #F8FAFC; color: #0F172A;
            }
            QLineEdit:focus { border: 2px solid #4F46E5; background-color: #EEF2FF; font-weight: bold; }
        """