import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


class QuickLoginDialog(QDialog):
    """ Modern Pop-up Gate - Keyboard Hidden by Default, Opens ONLY on Click/Touch """

    def __init__(self, parent=None, require_password=False):
        super().__init__(parent)
        self.require_password = require_password
        self.authenticated_user = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Verification")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel { color: #1E293B; font-size: 11px; font-weight: 500; font-family: 'Segoe UI'; }
            QLineEdit { 
                padding: 6px; 
                border: 1px solid #CBD5E1; 
                border-radius: 6px; 
                font-size: 12px; 
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLineEdit:focus { border: 2px solid #4F46E5; background-color: #F5F3FF; font-weight: bold; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(4)

        title = QLabel("Security Gate")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4F46E5; margin-bottom: 2px;")
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
                background-color: #4F46E5; color: white; padding: 10px; 
                font-size: 13px; font-weight: bold; border-radius: 6px; border: none;
                margin-top: 4px;
            }
            QPushButton:pressed { background-color: #4338CA; }
        """)
        verify_btn.clicked.connect(self.handle_verification)
        main_layout.addWidget(verify_btn)

        # ⌨️ حاوية لوحة المفاتيح
        self.keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(self.keyboard_widget)
        keyboard_layout.setContentsMargins(0, 4, 0, 0)
        keyboard_layout.setSpacing(4)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', '🔑 admin', 'Clear', '⌫', '🔽 Hide']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))

                if key in ['Clear', '⌫', '🔑 admin', '🔽 Hide']:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #E2E8F0; color: #334155; font-weight: bold; padding: 10px 2px; border-radius: 5px; border: none; font-size: 10px; }
                        QPushButton:pressed { background-color: #CBD5E1; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFFFF; color: #1E293B; font-weight: 600; padding: 10px 2px; border-radius: 5px; border: 1px solid #E2E8F0; font-size: 12px; }
                        QPushButton:pressed { background-color: #F1F5F9; border: 1px solid #CBD5E1; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        main_layout.addWidget(self.keyboard_widget)

        # 🔐 مخفي تماماً عند التشغيل الأولي (By Default)
        self.keyboard_widget.hide()

        # 🔥 تفعيل الـ Event Filter فقط في آخر الدالة بعد ضمان جرد وبناء كل الـ Objects بسلام
        self.username_input.installEventFilter(self)
        self.pin_input.installEventFilter(self)
        if self.require_password:
            self.password_input.installEventFilter(self)

        # إعطاء تركيز مبدئي صامت بدون إظهار الكيبورد
        self.current_focused_input = self.username_input
        self.username_input.setFocus()

    def handle_input_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)
        input_field.setFocus(Qt.OtherFocusReason)
        input_field.setCursorPosition(len(input_field.text()))

    def eventFilter(self, obj, event):
        # حماية شاملة: تأكدي أولاً من أن الحقول قد تم تهيئتها بالكامل بالذاكرة قبل المقارنة
        u_input = getattr(self, 'username_input', None)
        p_input = getattr(self, 'pin_input', None)
        pass_input = getattr(self, 'password_input', None)

        if obj in [u_input, p_input, pass_input] and obj is not None:
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
                self.keyboard_widget.show()
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()

        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        elif key == '🔑 admin':
            self.current_focused_input.setText("admin")
        elif key == '🔽 Hide':
            self.keyboard_widget.hide()
            return
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