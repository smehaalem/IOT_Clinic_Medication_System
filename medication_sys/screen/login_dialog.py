import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
import airtable_api


class QuickLoginDialog(QDialog):
    """ Unified Multi-Stage Security Gate supporting physical hardware keyboards. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.authenticated_user = None

        # State tracking flags
        self.is_manager_phase = False
        self.matched_user_record = None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Verification")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel { color: #1E293B; font-size: 14px; font-weight: bold; font-family: 'Segoe UI'; }
            QLineEdit { 
                padding: 10px; 
                border: 2px solid #CBD5E1; 
                border-radius: 8px; 
                font-size: 14px; 
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLineEdit:focus { border: 2px solid #4F46E5; background-color: #F5F3FF; font-weight: bold; }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(12)

        # Title
        self.title_lbl = QLabel("Security Gate")
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #4F46E5; margin-bottom: 5px;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title_lbl)

        # 👤 Username Field
        self.main_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.main_layout.addWidget(self.username_input)

        # 🔢 PIN Code Field (Visible during Stage 1)
        self.pin_lbl = QLabel("PIN Code")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("••••")
        self.main_layout.addWidget(self.pin_lbl)
        self.main_layout.addWidget(self.pin_input)

        # 🔑 Manager Password Field (Hidden initially until Stage 2 trigger)
        self.pass_lbl = QLabel("Manager Password")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter secure manager password")

        self.main_layout.addWidget(self.pass_lbl)
        self.main_layout.addWidget(self.password_input)

        # Hide Password layout parameters initially
        self.pass_lbl.hide()
        self.password_input.hide()

        # Submit Trigger Button
        self.verify_btn = QPushButton("Verify Identity")
        self.verify_btn.setMinimumHeight(48)
        self.verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5; color: white; 
                font-size: 15px; font-weight: bold; border-radius: 8px; border: none;
                margin-top: 10px;
            }
            QPushButton:pressed { background-color: #4338CA; }
        """)
        self.verify_btn.clicked.connect(self.process_auth_submission)
        self.main_layout.addWidget(self.verify_btn)

        self.username_input.setFocus()

    def process_auth_submission(self):
        """ Dynamically branches authentication routing inside a single layout context """
        un = self.username_input.text().strip()
        if not un:
            QMessageBox.warning(self, "Input Error", "Username field cannot be left blank.")
            return

        # 🛑 CASE B: Currently in Stage 2 (Manager Password Challenge Verification)
        if self.is_manager_phase:
            pwd = self.password_input.text().strip()
            if not pwd:
                QMessageBox.warning(self, "Input Error", "Manager Password field cannot be left blank.")
                return

            db_pass = str(self.matched_user_record.get("Password", "")).strip().split(".")[0]
            if db_pass == pwd:
                self.authenticated_user = self.matched_user_record
                self.accept()
            else:
                QMessageBox.critical(self, "Access Denied", "Incorrect Manager security password validation.")
            return

        # 🔓 CASE A: Currently in Stage 1 (Initial Username + PIN Scan)
        pin = self.pin_input.text().strip()
        if not pin:
            QMessageBox.warning(self, "Input Error", "PIN field cannot be left blank.")
            return

        try:
            all_users = airtable_api.get_all_users()
            user_match = None

            for u in all_users:
                db_user = str(u.get("Username", "")).strip()
                db_pin_raw = str(u.get("PIN Code", "")).strip()
                db_pin = db_pin_raw.split(".")[0] if "." in db_pin_raw else db_pin_raw

                if db_user.lower() == un.lower() and db_pin == pin:
                    user_match = u
                    break

            if not user_match:
                QMessageBox.critical(self, "Access Denied", "Incorrect Username or numeric PIN Code.")
                return

            # Extract privilege signature configuration safely
            role_val = user_match.get("Role", "User")
            if isinstance(role_val, list): role_val = role_val[0] if role_val else "User"
            user_role = str(role_val).strip().lower()

            # Dynamic Switch: If user is manager, transition the active view context into Phase 2
            if user_role == "maneger":
                self.is_manager_phase = True
                self.matched_user_record = user_match

                # Smooth UI Transformation inside the exact same pop-up window frame
                self.pin_lbl.hide()
                self.pin_input.hide()

                self.pass_lbl.show()
                self.password_input.show()

                # Freeze Username field to guarantee perfect immutable UX properties
                self.username_input.setReadOnly(True)
                self.username_input.setStyleSheet("""
                    padding: 10px; border: 2px solid #E2E8F0; border-radius: 8px; 
                    font-size: 14px; background-color: #F1F5F9; color: #64748B; font-weight: 500;
                """)

                self.password_input.setFocus()
            else:
                # Regular clinical staff (Doctor/Nurse) authenticated -> Bypass password step entirely
                self.authenticated_user = user_match
                self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Cloud lookup transaction failed: {str(e)}")