import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLineEdit, QDialog, QStackedWidget, QApplication,
    QTableWidget, QTableWidgetItem, QComboBox, QScrollArea, QFrame, QScroller
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
from datetime import datetime

import airtable_api


class QuickLoginDialog(QDialog):
    """ Modern, elegant Pop-up Authentication Gate """

    def __init__(self, parent=None, require_password=False, *args, **kwargs):
        super().__init__(parent)
        self.require_password = kwargs.get('require_password', require_password)
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

        # ---- Modern Embedded Keyboard ----
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


class UserManagementPage(QWidget):
    """ Modernized Admin Panel Workspace """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.editing_record_id = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #FFFFFF; font-family: 'Segoe UI'; color: #334155; }
            QLabel { font-size: 13px; font-weight: 500; color: #475569; }
            QLineEdit { 
                padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; 
                font-size: 13px; background-color: #F8FAFC; 
            }
            QLineEdit:focus { border: 2px solid #6366F1; background-color: #FFFFFF; }
            QComboBox { padding: 8px; border: 1px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; }
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # LEFT SIDE: Directory Table View
        left_layout = QVBoxLayout()
        header_layout = QHBoxLayout()

        table_title = QLabel("System User Directory")
        table_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")

        back_btn = QPushButton("⬅️ Back to Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton { padding: 6px 14px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; border: 1px solid #E2E8F0; color: #475569; }
            QPushButton:pressed { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.reset_form_state)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(table_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        self.users_table_widget = QTableWidget()
        self.users_table_widget.setColumnCount(3)
        self.users_table_widget.setHorizontalHeaderLabels(["Username", "Role Privilege", "Actions"])
        self.users_table_widget.setColumnWidth(0, 140)
        self.users_table_widget.setColumnWidth(1, 140)
        self.users_table_widget.setColumnWidth(2, 110)
        self.users_table_widget.setFrameShape(QFrame.NoFrame)
        self.users_table_widget.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; background-color: #FFFFFF; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; border: none; padding: 6px; color: #475569; }
        """)
        left_layout.addWidget(self.users_table_widget)

        refresh_btn = QPushButton("🔄 Refresh Cloud Directory")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("""
            QPushButton { padding: 12px; font-size: 13px; font-weight: bold; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; color: #475569;}
            QPushButton:pressed { background-color: #F1F5F9; }
        """)
        refresh_btn.clicked.connect(self.load_users_data)
        left_layout.addWidget(refresh_btn)
        main_layout.addLayout(left_layout, stretch=4)

        # RIGHT SIDE: Management Panel
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(6)

        self.form_title = QLabel("Register New System Account")
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4F46E5; margin-bottom: 4px;")
        right_layout.addWidget(self.form_title)

        right_layout.addWidget(QLabel("Full Name"))
        self.fullname_input = QLineEdit()
        self.fullname_input.focusInEvent = lambda event: self.handle_input_focus(self.fullname_input, event)
        right_layout.addWidget(self.fullname_input)

        right_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.focusInEvent = lambda event: self.handle_input_focus(self.username_input, event)
        right_layout.addWidget(self.username_input)

        right_layout.addWidget(QLabel("Password / Security Key"))
        self.password_input = QLineEdit()
        self.password_input.focusInEvent = lambda event: self.handle_input_focus(self.password_input, event)
        right_layout.addWidget(self.password_input)

        right_layout.addWidget(QLabel("System PIN Code"))
        self.pincode_input = QLineEdit()
        self.pincode_input.focusInEvent = lambda event: self.handle_input_focus(self.pincode_input, event)
        right_layout.addWidget(self.pincode_input)

        right_layout.addWidget(QLabel("System Privilege level"))
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["Maneger", "Doctor", "Nurse", "Assistant"])
        right_layout.addWidget(self.role_combobox)

        self.submit_btn = QPushButton("➕ Confirm Access Registration")
        self.submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_btn.setStyleSheet("""
            QPushButton { background-color: #4F46E5; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; margin-top: 4px;}
            QPushButton:pressed { background-color: #4338CA; }
        """)
        self.submit_btn.clicked.connect(self.handle_save_user)
        right_layout.addWidget(self.submit_btn)

        self.cancel_edit_btn = QPushButton("❌ Cancel Editing")
        self.cancel_edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cancel_edit_btn.setStyleSheet("""
            QPushButton { background-color: #EF4444; color: white; padding: 8px; font-weight: 600; border-radius: 8px; border: none; }
            QPushButton:pressed { background-color: #DC2626; }
        """)
        self.cancel_edit_btn.clicked.connect(self.reset_form_state)
        self.cancel_edit_btn.hide()
        right_layout.addWidget(self.cancel_edit_btn)

        # Embedded Form Virtual Keyboard
        right_layout.addWidget(QLabel("Form Virtual Input Board:"))
        keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 2, 0, 0)
        keyboard_layout.setSpacing(4)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '_'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', '⌫']
        ]
        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))
                if key in ['Clear', '⌫']:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 8px 3px; border-radius: 6px; border: none; font-size: 11px; }
                        QPushButton:pressed { background-color: #94A3B8; }
                    """)
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet("""
                        QPushButton { background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 8px 3px; border-radius: 6px; border: 1px solid #E2E8F0; min-width: 45px; font-size: 11px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 8px 3px; border-radius: 6px; border: 1px solid #E2E8F0; font-size: 12px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        right_layout.addWidget(keyboard_widget)
        main_layout.addLayout(right_layout, stretch=3)
        self.setLayout(main_layout)
        self.current_focused_input = self.fullname_input
        self.fullname_input.setFocus()

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
        else:
            self.current_focused_input.setText(current_text + key)
        self.current_focused_input.setFocus(Qt.OtherFocusReason)
        self.current_focused_input.setCursorPosition(len(self.current_focused_input.text()))

    def load_users_data(self):
        try:
            users = airtable_api.get_all_users()
            self.users_table_widget.setRowCount(0)
            for row_idx, user_data in enumerate(users):
                self.users_table_widget.insertRow(row_idx)
                role_val = user_data.get("Role", "N/A")
                if isinstance(role_val, list): role_val = role_val[0] if role_val else "N/A"
                u_item = QTableWidgetItem(str(user_data.get("Username", "N/A")))
                r_item = QTableWidgetItem(str(role_val))
                u_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                r_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.users_table_widget.setItem(row_idx, 0, u_item)
                self.users_table_widget.setItem(row_idx, 1, r_item)

                actions_widget = QWidget()
                actions_widget.setStyleSheet("background-color: transparent;")
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                actions_layout.setSpacing(6)

                edit_icon_btn = QPushButton("✏️")
                edit_icon_btn.setFixedWidth(35)
                edit_icon_btn.setStyleSheet(
                    "background-color: #0EA5E9; color: white; border-radius: 6px; font-weight: bold; border: none; padding: 4px;")
                edit_icon_btn.clicked.connect(lambda checked, u=user_data: self.prepare_edit_user(u))

                delete_icon_btn = QPushButton("❌")
                delete_icon_btn.setFixedWidth(35)
                delete_icon_btn.setStyleSheet(
                    "background-color: #EF4444; color: white; border-radius: 6px; font-weight: bold; border: none; padding: 4px;")
                delete_icon_btn.clicked.connect(lambda checked, u=user_data: self.handle_delete_user(u))

                actions_layout.addWidget(edit_icon_btn)
                actions_layout.addWidget(delete_icon_btn)
                actions_layout.addStretch()
                self.users_table_widget.setCellWidget(row_idx, 2, actions_widget)
        except Exception as e:
            print(f"Error loading table data: {str(e)}")

    def prepare_edit_user(self, user_data):
        self.editing_record_id = user_data.get("record_id")
        self.fullname_input.setText(str(user_data.get("Full Name", "")))
        self.username_input.setText(str(user_data.get("Username", "")))
        self.password_input.setText(str(user_data.get("Password", "")))
        pin_raw = str(user_data.get("PIN Code", ""))
        self.pincode_input.setText(pin_raw.split(".")[0] if "." in pin_raw else pin_raw)
        role_val = user_data.get("Role", "Assistant")
        if isinstance(role_val, list): role_val = role_val[0] if role_val else "Assistant"
        index = self.role_combobox.findText(str(role_val))
        if index >= 0: self.role_combobox.setCurrentIndex(index)

        self.form_title.setText("📝 Edit System Account")
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #EA580C; margin-bottom: 2px;")
        self.submit_btn.setText("💾 Save Modified Changes")
        self.submit_btn.setStyleSheet(
            "background-color: #EA580C; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; margin-top: 4px;")
        self.cancel_edit_btn.show()

    def reset_form_state(self):
        self.editing_record_id = None
        self.fullname_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.pincode_input.clear()
        self.role_combobox.setCurrentIndex(0)
        self.form_title.setText("Register New System Account")
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4F46E5; margin-bottom: 2px;")
        self.submit_btn.setText("➕ Confirm Access Registration")
        self.submit_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; margin-top: 4px;")
        self.cancel_edit_btn.hide()
        self.current_focused_input = self.fullname_input
        self.fullname_input.setFocus()

    def handle_save_user(self):
        full_name = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        pin_code = self.pincode_input.text().strip()
        role = self.role_combobox.currentText()
        if not full_name or not username or not password or not pin_code:
            QMessageBox.warning(self, "Validation Error", "All fields must be filled.")
            return
        try:
            if self.editing_record_id:
                record = airtable_api.update_user_records(self.editing_record_id, username, password, role, pin_code,
                                                          full_name)
                if record:
                    QMessageBox.information(self, "Success", f"Account '{username}' updated live.")
                    self.reset_form_state()
                    self.load_users_data()
            else:
                record = airtable_api.add_new_user(username, password, role, pin_code, full_name)
                if record:
                    QMessageBox.information(self, "Success", f"Account '{username}' registered live.")
                    self.reset_form_state()
                    self.load_users_data()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save user: {str(e)}")

    def handle_delete_user(self, user_data):
        username = user_data.get("Username", "Unknown")
        record_id = user_data.get("record_id")
        confirm = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete '{username}'?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                if airtable_api.delete_user_record(record_id):
                    QMessageBox.information(self, "Deleted", f"Account '{username}' removed.")
                    if self.editing_record_id == record_id: self.reset_form_state()
                    self.load_users_data()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Error: {str(e)}")


class MedicationManagementPage(QWidget):
    """ Modern, Fluid Live Stock Ingestion Panel """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.current_focused_input = None
        self.existing_record_id = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #FFFFFF; font-family: 'Segoe UI'; color: #334155; }
            QLabel { font-size: 13px; font-weight: 500; color: #475569; }
            QLineEdit { 
                padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; 
                font-size: 13px; background-color: #F8FAFC; 
            }
            QLineEdit:focus { border: 2px solid #0D9488; background-color: #FFFFFF; }
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 📜 LEFT COLUMN: Scrollable Form Workspace
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 40px; border-radius: 4px; }
        """)

        QScroller.grabGesture(self.scroll_area.viewport(), QScroller.LeftMouseButtonGesture)

        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)
        form_layout.setContentsMargins(5, 5, 12, 5)
        form_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        page_title = QLabel("📦 Stock Management Engine")
        page_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")

        back_btn = QPushButton("⬅️ Back")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton { padding: 5px 12px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; border: 1px solid #E2E8F0; color: #475569; }
            QPushButton:pressed { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.clear_all_fields)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        form_layout.addLayout(header_layout)

        form_layout.addWidget(QLabel("Step 1: Scan Barcode Identity"))
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan product barcode scanner...")
        self.barcode_input.setStyleSheet(
            "padding: 10px; border: 2px solid #0EA5E9; border-radius: 8px; font-weight: bold; font-size: 14px; background-color: #F0F9FF;")
        self.barcode_input.focusInEvent = lambda event: self.handle_input_focus(self.barcode_input, event)
        self.barcode_input.returnPressed.connect(self.handle_barcode_lookup)
        form_layout.addWidget(self.barcode_input)

        lookup_btn = QPushButton("🔍 Manual Cloud Lookup Verification")
        lookup_btn.setStyleSheet("""
            QPushButton { background-color: #0EA5E9; color: white; padding: 10px; font-weight: bold; border-radius: 8px; border: none; }
            QPushButton:pressed { background-color: #0284C7; }
        """)
        lookup_btn.clicked.connect(self.handle_barcode_lookup)
        form_layout.addWidget(lookup_btn)

        form_layout.addWidget(QLabel("Medicine Name"))
        self.med_name_input = QLineEdit()
        self.med_name_input.focusInEvent = lambda event: self.handle_input_focus(self.med_name_input, event)
        form_layout.addWidget(self.med_name_input)

        form_layout.addWidget(QLabel("Active Pharmaceutical Ingredient"))
        self.ingredient_input = QLineEdit()
        self.ingredient_input.focusInEvent = lambda event: self.handle_input_focus(self.ingredient_input, event)
        form_layout.addWidget(self.ingredient_input)

        form_layout.addWidget(QLabel("Dosage Strength (mg/ml)"))
        self.dosage_input = QLineEdit()
        self.dosage_input.focusInEvent = lambda event: self.handle_input_focus(self.dosage_input, event)
        form_layout.addWidget(self.dosage_input)

        form_layout.addWidget(QLabel("Batch Number / Serial"))
        self.batch_input = QLineEdit()
        self.batch_input.focusInEvent = lambda event: self.handle_input_focus(self.batch_input, event)
        form_layout.addWidget(self.batch_input)

        form_layout.addWidget(QLabel("Product Expiry Date (YYYY-MM-DD)"))
        self.expiry_input = QLineEdit()
        self.expiry_input.setPlaceholderText("2027-12-31")
        self.expiry_input.focusInEvent = lambda event: self.handle_input_focus(self.expiry_input, event)
        form_layout.addWidget(self.expiry_input)

        form_layout.addWidget(QLabel("Pills Count (Quantity Received)"))
        self.quantity_input = QLineEdit()
        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event)
        form_layout.addWidget(self.quantity_input)

        self.submit_med_btn = QPushButton("💾 Commit New Stock to Cloud")
        self.submit_med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_med_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; padding: 14px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px; margin-top: 6px;}
            QPushButton:pressed { background-color: #0F766E; }
        """)
        self.submit_med_btn.clicked.connect(self.handle_add_or_update_medication)
        form_layout.addWidget(self.submit_med_btn)

        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area, stretch=4)

        # ⌨️ RIGHT COLUMN: Elegant Touch Keyboard
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 5, 0, 0)
        right_layout.addWidget(QLabel("Virtual Touch Input Workspace:"))

        keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 2, 0, 0)
        keyboard_layout.setSpacing(4)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', '⌫']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))
                if key in ['Clear', '⌫']:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 12px 4px; border-radius: 6px; border: none; font-size: 12px; }
                        QPushButton:pressed { background-color: #94A3B8; }
                    """)
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet("""
                        QPushButton { background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 12px 4px; border-radius: 6px; border: 1px solid #E2E8F0; min-width: 55px; font-size: 12px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 12px 4px; border-radius: 6px; border: 1px solid #E2E8F0; font-size: 13px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        right_layout.addWidget(keyboard_widget)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, stretch=5)

        self.current_focused_input = self.barcode_input
        self.barcode_input.setFocus()

    def handle_input_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)
        input_field.setFocus(Qt.OtherFocusReason)
        input_field.setCursorPosition(len(input_field.text()))
        self.scroll_area.ensureWidgetVisible(input_field, 0, 60)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)
        self.current_focused_input.setFocus(Qt.OtherFocusReason)
        self.current_focused_input.setCursorPosition(len(self.current_focused_input.text()))

    def handle_barcode_lookup(self):
        barcode = self.barcode_input.text().strip()
        if not barcode: return
        try:
            record = airtable_api.find_medication_by_barcode(barcode)
            if record:
                self.existing_record_id = record.get('id') if isinstance(record, dict) else getattr(record, 'id', None)
                fields = record.fields if hasattr(record, 'fields') else record.get('fields', {})

                self.med_name_input.setText(str(fields.get("Medicine Name", "")))
                self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                self.dosage_input.setText(str(fields.get("Dosage", "")))
                self.batch_input.setText(str(fields.get("A Batch", fields.get("Batch Number", ""))))
                self.expiry_input.setText(str(fields.get("Expiry Date", "")))
                self.quantity_input.setText(str(fields.get("Current Pills Count", "")))

                self.submit_med_btn.setText("🆙 Update Existing Cloud Record")
                self.submit_med_btn.setStyleSheet("""
                    QPushButton { background-color: #2563EB; color: white; padding: 14px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px; margin-top: 6px;}
                    QPushButton:pressed { background-color: #1D4ED8; }
                """)

                QMessageBox.information(self, "Cloud Record Found",
                                        "Existing product fully loaded! You can edit fields to update the record.")
                self.quantity_input.setFocus()
            else:
                self.existing_record_id = None
                self.submit_med_btn.setText("💾 Commit New Stock to Cloud")
                self.submit_med_btn.setStyleSheet("""
                    QPushButton { background-color: #0D9488; color: white; padding: 14px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px; margin-top: 6px;}
                    QPushButton:pressed { background-color: #0F766E; }
                """)
                QMessageBox.information(self, "New Item",
                                        "Barcode not registered before. Please input details manually.")
                self.med_name_input.setFocus()
        except Exception as e:
            print(f"Error looking up barcode: {e}")

    def handle_add_or_update_medication(self):
        barcode = self.barcode_input.text().strip()
        name = self.med_name_input.text().strip()
        ingredient = self.ingredient_input.text().strip()
        dosage = self.dosage_input.text().strip()
        batch = self.batch_input.text().strip()
        expiry = self.expiry_input.text().strip()
        qty_str = self.quantity_input.text().strip()

        if not barcode or not name or not qty_str or not expiry:
            QMessageBox.warning(self, "Input Error", "Barcode, Name, Expiry, and Quantity are mandatory.")
            return

        expiry_date = None
        current_date = datetime.now().date()
        try:
            expiry_date = datetime.strptime(expiry, "%d-%m-%Y").date()
        except ValueError:
            try:
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            except ValueError:
                pass

        if not expiry_date:
            QMessageBox.warning(self, "Date Format Error 📅", "Invalid date format! Use DD-MM-YYYY or YYYY-MM-DD.")
            return

        if expiry_date < current_date:
            QMessageBox.critical(self, "Expired Medication ❌",
                                 f"Cannot save! The entered expiry date ({expiry_date.strftime('%d-%m-%Y')}) is in the past.")
            return

        try:
            qty = int(qty_str)
            clean_expiry_str = expiry_date.strftime("%Y-%m-%d")

            if self.existing_record_id:
                confirm = QMessageBox.question(
                    self,
                    "Confirm Stock Update ❓",
                    f"Are you sure you want to permanently save the modified changes for '{name}' to the cloud server?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if confirm != QMessageBox.Yes: return

                record = airtable_api.update_medication_full_fields(
                    self.existing_record_id, name, barcode, ingredient, dosage, clean_expiry_str, qty, batch
                )
                if record:
                    QMessageBox.information(self, "Stock Updated ✅",
                                            f"Successfully updated '{name}' details in the cloud live!")
                    self.clear_all_fields()
            else:
                record = airtable_api.add_new_medication(name, barcode, ingredient, dosage, clean_expiry_str, qty, qty,
                                                         batch)
                if record:
                    QMessageBox.information(self, "Stock Ingested",
                                            f"Successfully recorded new batch of {name} to cloud!")
                    self.clear_all_fields()

        except ValueError:
            QMessageBox.warning(self, "Type Error", "Pills Count must be a valid integer number.")
        except Exception as e:
            QMessageBox.critical(self, "Server Error", f"Failed to sync with Airtable: {e}")

    def clear_all_fields(self):
        self.barcode_input.clear()
        self.med_name_input.clear()
        self.ingredient_input.clear()
        self.dosage_input.clear()
        self.batch_input.clear()
        self.expiry_input.clear()
        self.quantity_input.clear()
        self.existing_record_id = None
        self.submit_med_btn.setText("💾 Commit New Stock to Cloud")
        self.submit_med_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; padding: 14px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px; margin-top: 6px;}
            QPushButton:pressed { background-color: #0F766E; }
        """)
        self.current_focused_input = self.barcode_input
        self.barcode_input.setFocus()


class MedicineSystemApp(QWidget):
    """ Modern Dashboard Layout Navigation Core """

    def __init__(self):
        super().__init__()
        self.resize(920, 620)
        self.setWindowTitle("Clinic Operations Infrastructure")
        self.setStyleSheet("QWidget { font-family: 'Segoe UI'; }")

        self.stack = QStackedWidget(self)
        self.build_main_menu_screen()
        self.build_medicine_sub_menu()

        self.admin_page = UserManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.admin_page)

        self.med_management_page = MedicationManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.med_management_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def build_main_menu_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        title = QLabel("Clinic Operations Management")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #0F172A; margin-bottom: 5px;")
        layout.addWidget(title)

        med_btn = QPushButton("💊 Medicine Stock Workspace")
        med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        med_btn.setStyleSheet(self.get_menu_button_style("#4F46E5", "#4338CA"))
        med_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(med_btn)

        patient_btn = QPushButton("👥 Patient File Workspace")
        patient_btn.setCursor(QCursor(Qt.PointingHandCursor))
        patient_btn.setStyleSheet(self.get_menu_button_style("#475569", "#334155"))
        patient_btn.clicked.connect(
            lambda: QMessageBox.information(self, "Workspace", "Loading Patient Records Workspace..."))
        layout.addWidget(patient_btn)

        self.stack.addWidget(page)

    def build_medicine_sub_menu(self):
        page = QWidget()
        page.setStyleSheet("background-color: #FFFFFF;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        title = QLabel("Medicine Control Operations")
        title.setStyleSheet("font-size: 23px; font-weight: bold; color: #1E293B; margin-bottom: 10px;")
        layout.addWidget(title)

        add_med_btn = QPushButton("➕ Add New Medication")
        add_med_btn.setStyleSheet(self.get_menu_button_style("#0D9488", "#0F766E"))
        add_med_btn.clicked.connect(lambda: self.trigger_secure_action("Add Medicine"))
        layout.addWidget(add_med_btn)

        manager_btn = QPushButton("🔑 Manager Administration Portal")
        manager_btn.setStyleSheet(self.get_menu_button_style("#D97706", "#B45309"))
        manager_btn.clicked.connect(self.trigger_manager_portal)
        layout.addWidget(manager_btn)

        dispense_btn = QPushButton("📦 Dispense / Deduct Quantity")
        dispense_btn.setStyleSheet(self.get_menu_button_style("#EF4444", "#DC2626"))
        dispense_btn.clicked.connect(lambda: self.trigger_secure_action("Dispense Medicine"))
        layout.addWidget(dispense_btn)

        back_btn = QPushButton("⬅️ Return to Main Menu")
        back_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #64748B; border: none; font-weight: bold; font-size: 14px; text-decoration: underline; margin-top: 10px;}
            QPushButton:hover { color: #475569; }
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn)

        self.stack.addWidget(page)

    def trigger_secure_action(self, action_name):
        dialog = QuickLoginDialog(self, require_password=False)
        if dialog.exec_() == QDialog.Accepted:
            if action_name == "Add Medicine":
                self.med_management_page.clear_all_fields()
                self.stack.setCurrentIndex(3)
            else:
                user = dialog.authenticated_user
                username = user.get("Username")
                role_val = user.get("Role", "User")
                if isinstance(role_val, list): role_val = role_val[0] if role_val else "User"

                QMessageBox.information(
                    self, "Permission Cleared",
                    f"Identity Confirmed: {username} ({role_val})\nExecuting: '{action_name}'"
                )

    def trigger_manager_portal(self):
        dialog = QuickLoginDialog(self, require_password=True)
        if dialog.exec_() == QDialog.Accepted:
            user = dialog.authenticated_user
            role_val = user.get("Role", "")
            if isinstance(role_val, list): role_val = role_val[0] if role_val else ""
            user_role = str(role_val).strip().lower()

            if user_role == "maneger":
                self.admin_page.load_users_data()
                self.stack.setCurrentIndex(2)
            else:
                QMessageBox.critical(self, "Security Error",
                                     f"Only verified 'Maneger' roles can enter this panel. Your role is: {role_val}")

    def get_menu_button_style(self, bg, press_bg):
        return f"""
            QPushButton {{
                background-color: {bg}; color: white;
                font-size: 15px; font-weight: bold;
                padding: 16px; border-radius: 12px; width: 320px; border: none;
            }}
            QPushButton:pressed {{ background-color: {press_bg}; }}
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineSystemApp()
    window.show()
    sys.exit(app.exec_())