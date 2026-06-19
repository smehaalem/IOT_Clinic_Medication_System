import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLineEdit, QDialog, QStackedWidget, QApplication,
    QTableWidget, QTableWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QScrollArea, QFrame
from PyQt5.QtWidgets import QScroller
from datetime import datetime

# Connect live to your established backend file
import airtable_api


class QuickLoginDialog(QDialog):
    """
    Unified Pop-up Authentication Dialog with integrated In-App Virtual Keyboard
    designed specifically for Raspberry Pi touchscreens.
    """

    def __init__(self, parent=None, require_password=False, *args, **kwargs):
        super().__init__(parent)
        self.require_password = kwargs.get('require_password', require_password)
        self.authenticated_user = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Verification")
        self.setFixedWidth(500)
        self.setStyleSheet("background-color: #FFFFFF;")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        title = QLabel("Security Gate")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2D3748; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        main_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet(
            "padding: 8px; border: 1.5px solid #CBD5E0; border-radius: 6px; font-size: 14px;")
        self.username_input.focusInEvent = lambda event: self.set_current_focus(self.username_input, event)
        main_layout.addWidget(self.username_input)

        main_layout.addWidget(QLabel("PIN Code:"))
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setStyleSheet("padding: 8px; border: 1.5px solid #CBD5E0; border-radius: 6px; font-size: 14px;")
        self.pin_input.focusInEvent = lambda event: self.set_current_focus(self.pin_input, event)
        main_layout.addWidget(self.pin_input)

        if self.require_password:
            main_layout.addWidget(QLabel("Manager Password:"))
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setStyleSheet(
                "padding: 8px; border: 1.5px solid #CBD5E0; border-radius: 6px; font-size: 14px;")
            self.password_input.focusInEvent = lambda event: self.set_current_focus(self.password_input, event)
            main_layout.addWidget(self.password_input)

        verify_btn = QPushButton("Verify Identity")
        verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        verify_btn.setStyleSheet(
            "background-color: #6200EA; color: white; padding: 10px; font-weight: bold; border-radius: 6px; margin-top: 5px; font-size: 14px;")
        verify_btn.clicked.connect(self.handle_verification)
        main_layout.addWidget(verify_btn)

        main_layout.addWidget(QLabel("Virtual Keyboard:"))
        keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.setSpacing(5)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', '🔑 admin', 'Clear', '⌫']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))
                if key in ['Clear', '⌫', '🔑 admin']:
                    btn.setStyleSheet(
                        "background-color: #E2E8F0; color: #2D3748; font-weight: bold; padding: 8px; border-radius: 4px; font-size: 12px;")
                else:
                    btn.setStyleSheet(
                        "background-color: #EDF2F7; color: #2D3748; padding: 8px; border-radius: 4px; font-weight: bold; font-size: 14px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        main_layout.addWidget(keyboard_widget)
        self.current_focused_input = self.username_input
        self.username_input.setFocus()

    def set_current_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)

    def handle_key_press(self, key):
        if not self.current_focused_input:
            return
        current_text = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        elif key == '🔑 admin':
            self.current_focused_input.setText("admin")
        else:
            self.current_focused_input.setText(current_text + key)

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
    """ Restricted System Admin Dashboard for user accounts. """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.editing_record_id = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #FFFFFF;")
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        table_title = QLabel("System User Directory")
        table_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A202C;")
        back_btn = QPushButton("⬅️ Back to Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("padding: 5px 10px; background-color: #E2E8F0; border-radius: 4px; font-weight: bold;")
        back_btn.clicked.connect(self.reset_form_state)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(table_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        self.users_table_widget = QTableWidget()
        self.users_table_widget.setColumnCount(3)
        self.users_table_widget.setHorizontalHeaderLabels(["Username", "System Privilege Role", "Actions ⚙️"])
        self.users_table_widget.setColumnWidth(0, 150)
        self.users_table_widget.setColumnWidth(1, 150)
        self.users_table_widget.setColumnWidth(2, 120)
        self.users_table_widget.setStyleSheet("font-size: 13px; color: #2D3748;")
        left_layout.addWidget(self.users_table_widget)

        refresh_btn = QPushButton("🔄 Refresh Database Records")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("padding: 10px; font-size: 13px; font-weight: bold; background-color: #EDF2F7;")
        refresh_btn.clicked.connect(self.load_users_data)
        left_layout.addWidget(refresh_btn)
        main_layout.addLayout(left_layout, stretch=5)

        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(8)

        self.form_title = QLabel("Register New System Account")
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4200FF; margin-bottom: 2px;")
        right_layout.addWidget(self.form_title)

        right_layout.addWidget(QLabel("Full Name:"))
        self.fullname_input = QLineEdit()
        self.fullname_input.setStyleSheet("padding: 6px; border: 1px solid #CBD5E0; border-radius: 4px;")
        self.fullname_input.focusInEvent = lambda event: self.set_current_focus(self.fullname_input, event)
        right_layout.addWidget(self.fullname_input)

        right_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("padding: 6px; border: 1px solid #CBD5E0; border-radius: 4px;")
        self.username_input.focusInEvent = lambda event: self.set_current_focus(self.username_input, event)
        right_layout.addWidget(self.username_input)

        right_layout.addWidget(QLabel("Password / Security Key:"))
        self.password_input = QLineEdit()
        self.password_input.setStyleSheet("padding: 6px; border: 1px solid #CBD5E0; border-radius: 4px;")
        self.password_input.focusInEvent = lambda event: self.set_current_focus(self.password_input, event)
        right_layout.addWidget(self.password_input)

        right_layout.addWidget(QLabel("System PIN Code:"))
        self.pincode_input = QLineEdit()
        self.pincode_input.setStyleSheet("padding: 6px; border: 1px solid #CBD5E0; border-radius: 4px;")
        self.pincode_input.focusInEvent = lambda event: self.set_current_focus(self.pincode_input, event)
        right_layout.addWidget(self.pincode_input)

        right_layout.addWidget(QLabel("System Level Permissions:"))
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["Maneger", "Doctor", "Nurse", "Assistant"])
        self.role_combobox.setStyleSheet("padding: 6px; background-color: #F8FAFC;")
        right_layout.addWidget(self.role_combobox)

        self.submit_btn = QPushButton("➕ Confirm Access Registration")
        self.submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_btn.setStyleSheet(
            "background-color: #6200EA; color: white; padding: 10px; font-weight: bold; border-radius: 4px; margin-top: 2px;")
        self.submit_btn.clicked.connect(self.handle_save_user)
        right_layout.addWidget(self.submit_btn)

        self.cancel_edit_btn = QPushButton("❌ Cancel Editing")
        self.cancel_edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cancel_edit_btn.setStyleSheet("background-color: #E53E3E; color: white; padding: 6px; border-radius: 4px;")
        self.cancel_edit_btn.clicked.connect(self.reset_form_state)
        self.cancel_edit_btn.hide()
        right_layout.addWidget(self.cancel_edit_btn)

        right_layout.addWidget(QLabel("Form Virtual Keyboard:"))
        keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.setSpacing(4)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '_'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', '⌫']
        ]
        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(3)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))
                if key in ['Clear', '⌫']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E0; color: #2D3748; font-weight: bold; padding: 6px; border-radius: 4px; font-size: 11px;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #EDF2F7; color: #2D3748; padding: 6px; border-radius: 4px; font-weight: bold; min-width: 50px;")
                else:
                    btn.setStyleSheet(
                        "background-color: #EDF2F7; color: #2D3748; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 12px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        right_layout.addWidget(keyboard_widget)
        main_layout.addLayout(right_layout, stretch=3)
        self.setLayout(main_layout)
        self.current_focused_input = self.fullname_input
        self.fullname_input.setFocus()

    def set_current_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)

    def handle_key_press(self, key):
        if not self.current_focused_input:
            return
        current_text = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)

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
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                actions_layout.setSpacing(4)

                edit_icon_btn = QPushButton("✏️")
                edit_icon_btn.setFixedWidth(35)
                edit_icon_btn.setStyleSheet(
                    "background-color: #3182CE; color: white; border-radius: 4px; font-weight: bold;")
                edit_icon_btn.clicked.connect(lambda checked, u=user_data: self.prepare_edit_user(u))

                delete_icon_btn = QPushButton("❌")
                delete_icon_btn.setFixedWidth(35)
                delete_icon_btn.setStyleSheet(
                    "background-color: #E53E3E; color: white; border-radius: 4px; font-weight: bold;")
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
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #DD6B20; margin-bottom: 2px;")
        self.submit_btn.setText("💾 Save Changes")
        self.submit_btn.setStyleSheet(
            "background-color: #DD6B20; color: white; padding: 10px; font-weight: bold; border-radius: 4px; margin-top: 2px;")
        self.cancel_edit_btn.show()

    def reset_form_state(self):
        self.editing_record_id = None
        self.fullname_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.pincode_input.clear()
        self.role_combobox.setCurrentIndex(0)
        self.form_title.setText("Register New System Account")
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4200FF; margin-bottom: 2px;")
        self.submit_btn.setText("➕ Confirm Access Registration")
        self.submit_btn.setStyleSheet(
            "background-color: #6200EA; color: white; padding: 10px; font-weight: bold; border-radius: 4px; margin-top: 2px;")
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


# =====================================================================
# 💊 الصفحة الجديدة المضافة: صفحة إضافة وإدارة الأدوية بالباركود والكيبورد
# =====================================================================

from PyQt5.QtWidgets import QScrollArea, QFrame, QScroller


class MedicationManagementPage(QWidget):
    """
    Restricted Live Medication Ingestion & Registration Panel.
    Optimized for small touchscreens with a dynamic left-side ScrollArea to easily
    reach all input fields and the action button.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #FFFFFF;")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # =====================================================================
        # 📜 LEFT COLUMN: Scrollable Form Widget
        # =====================================================================
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: #EDF2F7;
                width: 16px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E0;
                min-height: 40px;
                border-radius: 4px;
            }
        """)

        # تفعيل ميزة السحب باللمس الذكي (Kinetic/Gesture Scrolling) لشاشات الراسببيري باي
        QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)

        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)
        form_layout.setContentsMargins(5, 5, 15, 5)
        form_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        page_title = QLabel("📦 Stock Ingestion Engine")
        page_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C5282;")

        back_btn = QPushButton("⬅️ Back")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "padding: 3px 8px; background-color: #E2E8F0; border-radius: 4px; font-weight: bold; font-size: 11px;")
        back_btn.clicked.connect(self.clear_all_fields)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        form_layout.addLayout(header_layout)

        # Barcode Field
        form_layout.addWidget(QLabel("Step 1: Scan Barcode or Enter Value:"))
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode...")
        self.barcode_input.setStyleSheet(
            "padding: 6px; border: 2px solid #4299E1; border-radius: 5px; font-weight: bold; font-size: 13px;")
        self.barcode_input.focusInEvent = lambda event: self.set_current_focus(self.barcode_input, event)
        self.barcode_input.returnPressed.connect(self.handle_barcode_lookup)
        form_layout.addWidget(self.barcode_input)

        lookup_btn = QPushButton("🔍 Manual Cloud Check")
        lookup_btn.setStyleSheet(
            "background-color: #4299E1; color: white; padding: 5px; border-radius: 4px; font-weight: bold; font-size: 12px;")
        lookup_btn.clicked.connect(self.handle_barcode_lookup)
        form_layout.addWidget(lookup_btn)

        # Remaining Form Fields
        form_layout.addWidget(QLabel("Medicine Name:"))
        self.med_name_input = QLineEdit()
        self.med_name_input.setStyleSheet(
            "padding: 5px; border: 1px solid #CBD5E0; border-radius: 4px; font-size: 12px;")
        self.med_name_input.focusInEvent = lambda event: self.set_current_focus(self.med_name_input, event)
        form_layout.addWidget(self.med_name_input)

        form_layout.addWidget(QLabel("Active Ingredient:"))
        self.ingredient_input = QLineEdit()
        self.ingredient_input.setStyleSheet(
            "padding: 5px; border: 1px solid #CBD5E0; border-radius: 4px; font-size: 12px;")
        self.ingredient_input.focusInEvent = lambda event: self.set_current_focus(self.ingredient_input, event)
        form_layout.addWidget(self.ingredient_input)

        form_layout.addWidget(QLabel("Dosage (e.g., 500mg, 10ml):"))
        self.dosage_input = QLineEdit()
        self.dosage_input.setStyleSheet("padding: 5px; border: 1px solid #CBD5E0; border-radius: 4px; font-size: 12px;")
        self.dosage_input.focusInEvent = lambda event: self.set_current_focus(self.dosage_input, event)
        form_layout.addWidget(self.dosage_input)

        form_layout.addWidget(QLabel("Batch Number / Serial:"))
        self.batch_input = QLineEdit()
        self.batch_input.setStyleSheet("padding: 5px; border: 1px solid #CBD5E0; border-radius: 4px; font-size: 12px;")
        self.batch_input.focusInEvent = lambda event: self.set_current_focus(self.batch_input, event)
        form_layout.addWidget(self.batch_input)

        form_layout.addWidget(QLabel("Expiry Date (Format: YYYY-MM-DD):"))
        self.expiry_input = QLineEdit()
        self.expiry_input.setPlaceholderText("2027-12-31")
        self.expiry_input.setStyleSheet("padding: 5px; border: 1px solid #CBD5E0; border-radius: 4px; font-size: 12px;")
        self.expiry_input.focusInEvent = lambda event: self.set_current_focus(self.expiry_input, event)
        form_layout.addWidget(self.expiry_input)

        form_layout.addWidget(QLabel("Pills Count (Quantity Received):"))
        self.quantity_input = QLineEdit()
        self.quantity_input.setStyleSheet(
            "padding: 5px; border: 1px solid #CBD5E0; border-radius: 4px; font-size: 12px;")
        self.quantity_input.focusInEvent = lambda event: self.set_current_focus(self.quantity_input, event)
        form_layout.addWidget(self.quantity_input)

        submit_med_btn = QPushButton("💾 Commit Stock to Cloud")
        submit_med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        submit_med_btn.setStyleSheet(
            "background-color: #319795; color: white; padding: 10px; font-weight: bold; border-radius: 5px; font-size: 13px; margin-top: 5px;")
        submit_med_btn.clicked.connect(self.handle_add_medication)
        form_layout.addWidget(submit_med_btn)

        # ربط الوعاء الداخلي بمنطقة التمرير
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=4)

        # =====================================================================
        # ⌨️ RIGHT COLUMN: Fully Embedded Touchscreen Virtual Keyboard
        # =====================================================================
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 5, 0, 0)
        right_layout.addWidget(QLabel("Virtual Input Board:"))

        keyboard_widget = QWidget()
        keyboard_layout = QVBoxLayout(keyboard_widget)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.setSpacing(3)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', '⌫']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(3)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))
                if key in ['Clear', '⌫']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E0; color: #2D3748; font-weight: bold; padding: 8px 4px; border-radius: 4px; font-size: 11px;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #EDF2F7; color: #2D3748; padding: 8px 4px; border-radius: 4px; font-weight: bold; min-width: 50px; font-size: 11px;")
                else:
                    btn.setStyleSheet(
                        "background-color: #EDF2F7; color: #2D3748; padding: 8px 4px; border-radius: 4px; font-weight: bold; font-size: 12px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        right_layout.addWidget(keyboard_widget)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, stretch=5)

        self.current_focused_input = self.barcode_input
        self.barcode_input.setFocus()

    def set_current_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)

    def handle_barcode_lookup(self):
        barcode = self.barcode_input.text().strip()
        if not barcode: return
        try:
            record = airtable_api.find_medication_by_barcode(barcode)
            if record:
                fields = record.fields if hasattr(record, 'fields') else record.get('fields', {})
                self.med_name_input.setText(str(fields.get("Medicine Name", "")))
                self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                self.dosage_input.setText(str(fields.get("Dosage", "")))
                QMessageBox.information(self, "Cloud Record Found",
                                        "Existing medication template loaded automatically!")
                self.batch_input.setFocus()
            else:
                QMessageBox.information(self, "New Item",
                                        "Barcode not registered before. Please input details manually.")
                self.med_name_input.setFocus()
        except Exception as e:
            print(f"Error looking up barcode: {e}")

    def handle_add_medication(self):
        barcode = self.barcode_input.text().strip()
        name = self.med_name_input.text().strip()
        ingredient = self.ingredient_input.text().strip()
        dosage = self.dosage_input.text().strip()
        batch = self.batch_input.text().strip()
        expiry = self.expiry_input.text().strip()
        qty_str = self.quantity_input.text().strip()

        # 1. الفحص الأساسي للحقول المطلوبة
        if not barcode or not name or not qty_str or not expiry:
            QMessageBox.warning(self, "Input Error", "Barcode, Name, Expiry, and Quantity are mandatory.")
            return

        # 2. 🔥 فحص مرن لصيغة التاريخ وصلاحيته (يدعم الإدخال باليوم أو بالسنة)
        expiry_date = None
        current_date = datetime.now().date()

        # تجربة الصيغة الأولى: DD-MM-YYYY (الشائعة في الإدخال اليدوي مثل 12-12-2018)
        try:
            expiry_date = datetime.strptime(expiry, "%d-%m-%Y").date()
        except ValueError:
            # تجربة الصيغة الثانية إذا فشلت الأولى: YYYY-MM-DD (القياسية مثل 2018-12-12)
            try:
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            except ValueError:
                pass

        # إذا فشلت المحاولتان، يعني أن الصيغة خاطئة تماماً
        if not expiry_date:
            QMessageBox.warning(
                self,
                "Date Format Error 📅",
                "Invalid date format!\n\nPlease use either:\n- DD-MM-YYYY (e.g., 31-12-2027)\n- YYYY-MM-DD (e.g., 2027-12-31)"
            )
            return

        # فحص إن كان التاريخ في الماضي (منتهي الصلاحية)
        if expiry_date < current_date:
            QMessageBox.critical(
                self,
                "Expired Medication ❌",
                f"Cannot add this medication!\n\nThe entered expiry date ({expiry_date.strftime('%d-%m-%Y')}) is in the past. This medication is expired."
            )
            return

        # 3. إكمال عملية الإدخال إلى السحاب إذا كان التاريخ سليماً وغير منتهٍ
        try:
            qty = int(qty_str)
            # نرسل الصيغة القياسية YYYY-MM-DD لـ Airtable لكي يقبلها السيرفر بدون مشاكل
            clean_expiry_str = expiry_date.strftime("%Y-%m-%d")

            record = airtable_api.add_new_medication(name, barcode, ingredient, dosage, clean_expiry_str, qty, qty,
                                                     batch)
            if record:
                QMessageBox.information(self, "Stock Ingested",
                                        f"Successfully recorded batch {batch} of {name} ({qty} pills) to cloud!")
                self.clear_all_fields()
        except ValueError:
            QMessageBox.warning(self, "Type Error", "Pills Count must be a valid integer number.")
        except Exception as e:
            QMessageBox.critical(self, "Server Error", f"Failed to push to Airtable: {e}")

    def clear_all_fields(self):
        self.barcode_input.clear()
        self.med_name_input.clear()
        self.ingredient_input.clear()
        self.dosage_input.clear()
        self.batch_input.clear()
        self.expiry_input.clear()
        self.quantity_input.clear()
        self.current_focused_input = self.barcode_input
        self.barcode_input.setFocus()

class MedicineSystemApp(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(900, 600)  # تعريض الأبعاد الكلية بشكل مثالي للشاشة والكيبورد
        self.setWindowTitle("Clinic Operations Infrastructure")

        self.stack = QStackedWidget(self)

        self.build_main_menu_screen()  # Index 0
        self.build_medicine_sub_menu()  # Index 1

        # تهيئة الصفحات الفرعية وتثبيت مراجع العودة للقائمة السابقة (Index 1)
        self.admin_page = UserManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.admin_page)  # Index 2

        self.med_management_page = MedicationManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.med_management_page)  # Index 3

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def build_main_menu_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F4F6F9;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("Clinic Operations Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1A202C; margin-bottom: 10px;")
        layout.addWidget(title)

        med_btn = QPushButton("💊 Medicine Management")
        med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        med_btn.setStyleSheet(self.get_menu_button_style("#6200EA"))
        med_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(med_btn)

        patient_btn = QPushButton("👥 Patient File Workspace")
        patient_btn.setCursor(QCursor(Qt.PointingHandCursor))
        patient_btn.setStyleSheet(self.get_menu_button_style("#4A5568"))
        patient_btn.clicked.connect(lambda: QMessageBox.information(self, "Workspace", "Loading Patient Records..."))
        layout.addWidget(patient_btn)

        self.stack.addWidget(page)

    def build_medicine_sub_menu(self):
        page = QWidget()
        page.setStyleSheet("background-color: #FFFFFF;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        title = QLabel("Medicine Control Operations")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2D3748; margin-bottom: 15px;")
        layout.addWidget(title)

        add_med_btn = QPushButton("➕ Add New Medication")
        add_med_btn.setStyleSheet(self.get_menu_button_style("#319795"))
        add_med_btn.clicked.connect(lambda: self.trigger_secure_action("Add Medicine"))
        layout.addWidget(add_med_btn)

        manager_btn = QPushButton("🔑 Manager Administration Portal")
        manager_btn.setStyleSheet(self.get_menu_button_style("#D69E2E"))
        manager_btn.clicked.connect(self.trigger_manager_portal)
        layout.addWidget(manager_btn)

        dispense_btn = QPushButton("📦 Dispense / Deduct Quantity")
        dispense_btn.setStyleSheet(self.get_menu_button_style("#E53E3E"))
        dispense_btn.clicked.connect(lambda: self.trigger_secure_action("Dispense Medicine"))
        layout.addWidget(dispense_btn)

        back_btn = QPushButton("⬅️ Return to Main Menu")
        back_btn.setStyleSheet(
            "background-color: transparent; color: #718096; border: none; font-weight: bold; text-decoration: underline; margin-top: 10px;")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn)

        self.stack.addWidget(page)

    def trigger_secure_action(self, action_name):
        dialog = QuickLoginDialog(self, require_password=False)
        if dialog.exec_() == QDialog.Accepted:
            # عند تصفية الأمان لزر الإضافة نقله لصفحة الأدوية (Index 3)
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

    def get_menu_button_style(self, color_hex):
        return f"""
            QPushButton {{
                background-color: {color_hex}; color: white;
                font-size: 15px; font-weight: bold;
                padding: 14px; border-radius: 8px; width: 300px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineSystemApp()
    window.show()
    sys.exit(app.exec_())