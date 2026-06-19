import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLineEdit, QDialog, QStackedWidget, QApplication,
    QTableWidget, QTableWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

# Connect live to your established backend file
import airtable_api


class QuickLoginDialog(QDialog):
    """
    Unified Pop-up Authentication Dialog.
    Prompts for Username and PIN Code, and optionally a Password for Managers.
    """

    def __init__(self, parent=None, require_password=False):
        super().__init__(parent)
        self.require_password = require_password
        self.authenticated_user = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Verification")
        self.setFixedWidth(340)
        self.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Security Gate")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2D3748; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Username Field
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("padding: 8px; border: 1.5px solid #CBD5E0; border-radius: 6px;")
        layout.addWidget(self.username_input)

        # PIN Code Field
        layout.addWidget(QLabel("PIN Code:"))
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setStyleSheet("padding: 8px; border: 1.5px solid #CBD5E0; border-radius: 6px;")
        layout.addWidget(self.pin_input)

        # Conditional Password Field for Manager panel access
        if self.require_password:
            layout.addWidget(QLabel("Manager Password:"))
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setStyleSheet("padding: 8px; border: 1.5px solid #CBD5E0; border-radius: 6px;")
            layout.addWidget(self.password_input)

        # Action Verification Button
        verify_btn = QPushButton("Verify Identity")
        verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        verify_btn.setStyleSheet(
            "background-color: #6200EA; color: white; padding: 10px; font-weight: bold; border-radius: 6px; margin-top: 5px;")
        verify_btn.clicked.connect(self.handle_verification)
        layout.addWidget(verify_btn)

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
                # 1. تنظيف اسم المستخدم ومطابقته بحالة أحرف صغيرة لتجنب الأخطاء
                db_user = str(u.get("Username", "")).strip()

                # 2. تنظيف الـ PIN Code من أي علامات عشرية (.0) قادمة من السيرفر
                db_pin_raw = str(u.get("PIN Code", "")).strip()
                if "." in db_pin_raw:
                    db_pin = db_pin_raw.split(".")[0]
                else:
                    db_pin = db_pin_raw

                # 3. فحص تطابق اسم المستخدم والـ PIN
                if db_user == username and db_pin == pin:
                    user_match = u
                    break

            if not user_match:
                QMessageBox.critical(self, "Access Denied", "Invalid Username or PIN Code.")
                return

            # 4. فحص كلمة المرور الإضافية للمدير إذا طلبت البوابة ذلك
            if self.require_password:
                password = self.password_input.text().strip()

                db_pass_raw = str(user_match.get("Password", "")).strip()
                if "." in db_pass_raw:
                    db_pass = db_pass_raw.split(".")[0]
                else:
                    db_pass = db_pass_raw

                if db_pass != password:
                    QMessageBox.critical(self, "Access Denied", "Incorrect Manager Security Password.")
                    return

            # تم التحقق بنجاح!
            self.authenticated_user = user_match
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Connection failed: {str(e)}")

class UserManagementPage(QWidget):
    """
    Restricted System Admin Dashboard.
    Accessible ONLY by users registered with 'Maneger' role privilege.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #FFFFFF;")
        main_layout = QHBoxLayout()

        # LEFT COLUMN: User Directory View Grid
        left_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        table_title = QLabel("System User Directory")
        table_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A202C;")

        back_btn = QPushButton("⬅️ Back to Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("padding: 5px 10px; background-color: #E2E8F0; border-radius: 4px; font-weight: bold;")
        back_btn.clicked.connect(self.on_back_to_menu)

        header_layout.addWidget(table_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        self.users_table_widget = QTableWidget()
        self.users_table_widget.setColumnCount(2)
        self.users_table_widget.setHorizontalHeaderLabels(["Username", "System Privilege Role"])
        self.users_table_widget.setColumnWidth(0, 200)
        self.users_table_widget.setColumnWidth(1, 200)
        self.users_table_widget.setStyleSheet("font-size: 13px; color: #2D3748;")
        left_layout.addWidget(self.users_table_widget)

        refresh_btn = QPushButton("🔄 Refresh Database Records")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("padding: 10px; font-size: 13px; font-weight: bold; background-color: #EDF2F7;")
        refresh_btn.clicked.connect(self.load_users_data)
        left_layout.addWidget(refresh_btn)

        main_layout.addLayout(left_layout, stretch=2)

        # RIGHT COLUMN: Restricted Creation Engine
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(12)

        form_title = QLabel("Register New System Account")
        form_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4A5568; margin-bottom: 5px;")
        right_layout.addWidget(form_title)

        right_layout.addWidget(QLabel("Full Name:"))
        self.fullname_input = QLineEdit()
        self.fullname_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E0; border-radius: 4px;")
        right_layout.addWidget(self.fullname_input)

        right_layout.addWidget(QLabel("New Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E0; border-radius: 4px;")
        right_layout.addWidget(self.username_input)

        right_layout.addWidget(QLabel("Temporary Password:"))
        self.password_input = QLineEdit()
        self.password_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E0; border-radius: 4px;")
        right_layout.addWidget(self.password_input)

        right_layout.addWidget(QLabel("System PIN Code:"))
        self.pincode_input = QLineEdit()
        self.pincode_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E0; border-radius: 4px;")
        right_layout.addWidget(self.pincode_input)

        right_layout.addWidget(QLabel("System Level Permissions:"))
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["Maneger", "Doctor", "Nurse", "Assistant"])
        self.role_combobox.setStyleSheet("padding: 8px; background-color: #F8FAFC;")
        right_layout.addWidget(self.role_combobox)

        submit_btn = QPushButton("➕ Confirm Access Registration")
        submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        submit_btn.setStyleSheet(
            "background-color: #6200EA; color: white; padding: 10px; font-weight: bold; border-radius: 4px; margin-top: 5px;")
        submit_btn.clicked.connect(self.handle_create_user)
        right_layout.addWidget(submit_btn)

        main_layout.addLayout(right_layout, stretch=1)
        self.setLayout(main_layout)

    def load_users_data(self):
        try:
            users = airtable_api.get_all_users()
            self.users_table_widget.setRowCount(0)
            for row_idx, user_data in enumerate(users):
                self.users_table_widget.insertRow(row_idx)

                # Dynamic cell safety extracting dropdown structures if wrapped inside list
                role_val = user_data.get("Role", "N/A")
                if isinstance(role_val, list):
                    role_val = role_val[0] if role_val else "N/A"

                u_item = QTableWidgetItem(str(user_data.get("Username", "N/A")))
                r_item = QTableWidgetItem(str(role_val))
                u_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                r_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.users_table_widget.setItem(row_idx, 0, u_item)
                self.users_table_widget.setItem(row_idx, 1, r_item)
        except Exception as e:
            print(f"Error loading table data: {str(e)}")

    def handle_create_user(self):
        full_name = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        pin_code = self.pincode_input.text().strip()
        role = self.role_combobox.currentText()

        if not full_name or not username or not password or not pin_code:
            QMessageBox.warning(self, "Validation Error", "All fields must be filled.")
            return

        try:
            record = airtable_api.add_new_user(username, password, role, pin_code, full_name)
            if record:
                QMessageBox.information(self, "Success", f"Account '{username}' registered live.")
                self.fullname_input.clear()
                self.username_input.clear()
                self.password_input.clear()
                self.pincode_input.clear()
                self.load_users_data()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to register user: {str(e)}")


class MedicineSystemApp(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(850, 550)
        self.setWindowTitle("Clinic Operations Infrastructure")

        self.stack = QStackedWidget(self)

        self.build_main_menu_screen()  # Index 0
        self.build_medicine_sub_menu()  # Index 1

        self.admin_page = UserManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.admin_page)  # Index 2

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
            user = dialog.authenticated_user
            username = user.get("Username")

            # Extract safe role representation
            role_val = user.get("Role", "User")
            if isinstance(role_val, list):
                role_val = role_val[0] if role_val else "User"

            QMessageBox.information(
                self, "Permission Cleared",
                f"Identity Confirmed: {username} ({role_val})\nExecuting: '{action_name}'"
            )

    def trigger_manager_portal(self):
        dialog = QuickLoginDialog(self, require_password=True)
        if dialog.exec_() == QDialog.Accepted:
            user = dialog.authenticated_user

            # Deep list/string extractor for single-select dropdown components
            role_val = user.get("Role", "")
            if isinstance(role_val, list):
                role_val = role_val[0] if role_val else ""

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