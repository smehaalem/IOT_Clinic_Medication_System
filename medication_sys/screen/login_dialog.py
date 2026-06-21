import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
import airtable_api

class QuickLoginDialog(QDialog):
    """ Modern, elegant Pop-up Authentication Gate """
    # 🔥 تعريف الدالة بشكل صريح وبدون *args أو **kwargs لمنع الـ TypeError
    def __init__(self, parent=None, require_password=False):
        super().__init__(parent)
        self.require_password = require_password
        self.authenticated_user = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Verification")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel { color: #1E293B; font-size: 13px; font-weight: 500; font-family: 'Segoe UI'; }
            QLineEdit { 
                padding: 12px; 
                border: 2px solid #E2E8F0; 
                border-radius: 10px; 
                font-size: 14px; 
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLineEdit:focus { border: 2px solid #6366F1; background-color: #F5F3FF; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        title = QLabel("Security Gate")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4F46E5; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        main_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.focusInEvent = lambda event: self.handle_input_focus(self.username_input, event)
        main_layout.addWidget(self.username_input)

        main_layout.addWidget(QLabel("PIN Code"))
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("••••")
        self.pin_input.focusInEvent = lambda event: self.handle_input_focus(self.pin_input, event)
        main_layout.addWidget(self.pin_input)

        if self.require_password:
            main_layout.addWidget(QLabel("Manager Password"))
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.focusInEvent = lambda event: self.handle_input_focus(self.password_input, event)
            main_layout.addWidget(self.password_input)

        verify_btn = QPushButton("Verify Identity")
        verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5; color: white; padding: 14px; 
                font-size: 15px; font-weight: bold; border-radius: 10px; border: none;
            }
            QPushButton:pressed { background-color: #4338CA; }
        """)
        verify_btn.clicked.connect(self.handle_verification)
        main_layout.addWidget(verify_btn)

        keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 10, 0, 0)
        keyboard_layout.setSpacing(6)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', '🔑 admin', 'Clear', '⌫']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(5)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))

                if key in ['Clear', '⌫', '🔑 admin']:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #E2E8F0; color: #334155; font-weight: bold; padding: 10px; border-radius: 8px; border: none; font-size: 12px; }
                        QPushButton:pressed { background-color: #CBD5E1; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFFFF; color: #1E293B; font-weight: 600; padding: 10px; border-radius: 8px; border: 1px solid #E2E8F0; font-size: 14px; }
                        QPushButton:pressed { background-color: #F1F5F9; border: 1px solid #CBD5E1; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        main_layout.addWidget(keyboard_widget)

        self.current_focused_input = self.username_input
        self.username_input.setFocus()

    def handle_input_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)
        input_field.setFocus(Qt.OtherFocusReason)
        input_field.setCursorPosition(len(input_field.text()))

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        elif key == '🔑 admin':
            self.current_focused_input.setText("admin")
        else:
            self.current_focused_input.setText(current_text + key)
        self.current_focused_input.setFocus(Qt.OtherFocusReason)
        self.current_focused_input.setCursorPosition(len(self.current_focused_input.text()))

    def handle_verification(self):
        username = self.username_input.text().strip()
        pin = self.pin_input.text().strip()
        if not username or not pin:
            QMessageBox.warning(self, "Input Error", "All fields must be filled.")
            return
        try:
            all_users = airtable_api.get_all_users()
            user_match = None
            for u in all_users:
                db_user = str(u.get("Username", "")).strip()
                db_pin_raw = str(u.get("PIN Code", "")).strip()
                db_pin = db_pin_raw.split(".")[0] if "." in db_pin_raw else db_pin_raw
                if db_user == username and db_pin == pin:
                    user_match = u
                    break
            if not user_match:
                QMessageBox.critical(self, "Access Denied", "Invalid Username or PIN Code.")
                return
            if self.require_password:
                password = self.password_input.text().strip()
                db_pass_raw = str(user_match.get("Password", "")).strip()
                db_pass = db_pass_raw.split(".")[0] if "." in db_pass_raw else db_pass_raw
                if db_pass != password:
                    QMessageBox.critical(self, "Access Denied", "Incorrect Manager Security Password.")
                    return
            self.authenticated_user = user_match
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Connection failed: {str(e)}")