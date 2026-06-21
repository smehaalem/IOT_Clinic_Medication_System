import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor


# ----------------------------------------------------
# MOCK BACKEND (For testing purposes)
# ----------------------------------------------------
class MockAirtableAPI:
    def __init__(self):
        # Initial mock database records
        self.mock_users = [
            {"Username": "admin", "Password": "123", "Role": "Clinic administrator"},
            {"Username": "doctor1", "Password": "123", "Role": "Doctor"},
            {"Username": "staff1", "Password": "123", "Role": "Inventory Staff"}
        ]

    def get_all_users(self):
        return self.mock_users

    def add_new_user(self, username, password, role):
        new_record = {"Username": username, "Password": password, "Role": role}
        self.mock_users.append(new_record)
        return new_record


# Instantiate the mock API globally for the test environment
airtable_api = MockAirtableAPI()


# ----------------------------------------------------
# 1. LOGIN PAGE COMPONENT
# ----------------------------------------------------
class LoginPage(QWidget):
    def __init__(self, parent=None, on_login_success=None):
        super().__init__(parent)
        self.on_login_success = on_login_success
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #F4F6F9;")

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        card_widget = QWidget()
        card_widget.setObjectName("CardWidget")
        card_widget.setFixedWidth(380)
        card_widget.setStyleSheet("""
            QWidget#CardWidget {
                background-color: #FFFFFF;
                border-radius: 12px;
                padding: 30px;
            }
        """)

        card_layout = QVBoxLayout(card_widget)
        card_layout.setSpacing(18)

        title_label = QLabel("Log In")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2D3748; margin-bottom: 10px;")
        card_layout.addWidget(title_label)

        # Username Input
        username_layout = QVBoxLayout()
        username_label = QLabel("Username")
        username_label.setStyleSheet("color: #4A5568; font-size: 13px; font-weight: bold;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Try: admin, doctor1, or staff1")
        self.username_input.setStyleSheet(self.get_input_style())
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        card_layout.addLayout(username_layout)

        # Password Input
        password_layout = QVBoxLayout()
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: #4A5568; font-size: 13px; font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Try: 123")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.get_input_style())
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        card_layout.addLayout(password_layout)

        # Login Action Button
        login_btn = QPushButton("Log In")
        login_btn.setCursor(QCursor(Qt.PointingHandCursor))
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200EA; 
                color: white; 
                font-size: 15px;
                font-weight: bold; 
                padding: 12px; 
                border-radius: 6px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #7C4DFF;
            }
        """)
        login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(login_btn)

        main_layout.addWidget(card_widget)
        self.setLayout(main_layout)

    def get_input_style(self):
        return """
            QLineEdit {
                border: 1.5px solid #CBD5E0;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                background-color: #F8FAFC;
                color: #2D3748;
            }
            QLineEdit:focus {
                border: 1.5px solid #6200EA;
                background-color: #FFFFFF;
            }
        """

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Both fields are required.")
            return

        users = airtable_api.get_all_users()
        authenticated_user = None

        for user in users:
            if user.get("Username") == username and user.get("Password") == password:
                authenticated_user = user
                break

        if authenticated_user:
            role = authenticated_user.get("Role", "Doctor")

            # Scenario A: User is a Manager -> Direct route to Admin Panel
            if role == "Clinic administrator":
                QMessageBox.information(self, "Access Granted", f"Welcome, Manager {username}! Accessing Admin Panel.")
                if self.on_login_success:
                    self.on_login_success(role)

            # Scenario B: Ordinary staff member -> Restricted from adding users
            else:
                QMessageBox.information(self, "Access Granted",
                                        f"Welcome {username}!\nYou logged in successfully as an authorized '{role}'.\n\n(Note: Medicine features load here. You don't have Manager rights to add users).")
        else:
            QMessageBox.critical(self, "Access Denied", "Invalid username or password.")


# ----------------------------------------------------
# 2. RESTRICTED USER MANAGEMENT PAGE (For Managers)
# ----------------------------------------------------
class UserManagementPage(QWidget):
    def __init__(self, parent=None, on_logout=None):
        super().__init__(parent)
        self.on_logout = on_logout
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #FFFFFF;")
        main_layout = QHBoxLayout()

        # Left Column - View Users
        left_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        table_title = QLabel("System User Directory")
        table_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A202C;")

        logout_btn = QPushButton("🚪 Logout")
        logout_btn.setCursor(QCursor(Qt.PointingHandCursor))
        logout_btn.setStyleSheet("padding: 5px 10px; background-color: #E2E8F0; border-radius: 4px; font-weight: bold;")
        logout_btn.clicked.connect(self.on_logout)

        header_layout.addWidget(table_title)
        header_layout.addStretch()
        header_layout.addWidget(logout_btn)
        left_layout.addLayout(header_layout)

        self.users_table_widget = QTableWidget()
        self.users_table_widget.setColumnCount(2)
        self.users_table_widget.setHorizontalHeaderLabels(["Username", "System Privilege Role"])
        self.users_table_widget.setColumnWidth(0, 180)
        self.users_table_widget.setColumnWidth(1, 180)
        left_layout.addWidget(self.users_table_widget)

        refresh_btn = QPushButton("🔄 Refresh Database Records")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #EDF2F7;")
        refresh_btn.clicked.connect(self.load_users_data)
        left_layout.addWidget(refresh_btn)

        main_layout.addLayout(left_layout, stretch=2)

        # Right Column - Add User Form
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(12)

        form_title = QLabel("Register New System Account")
        form_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4A5568; margin-bottom: 5px;")
        right_layout.addWidget(form_title)

        right_layout.addWidget(QLabel("New Username:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E0; border-radius: 4px;")
        right_layout.addWidget(self.username_input)

        right_layout.addWidget(QLabel("Temporary Password:"))
        self.password_input = QLineEdit()
        self.password_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E0; border-radius: 4px;")
        right_layout.addWidget(self.password_input)

        right_layout.addWidget(QLabel("System Level Permissions:"))
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["Clinic administrator", "Inventory Staff", "Doctor"])
        self.role_combobox.setStyleSheet("padding: 8px; background-color: #F8FAFC;")
        right_layout.addWidget(self.role_combobox)

        submit_btn = QPushButton("➕ Confirm Access Registration")
        submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        submit_btn.setStyleSheet(
            "background-color: #6200EA; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
        submit_btn.clicked.connect(self.handle_create_user)
        right_layout.addWidget(submit_btn)

        main_layout.addLayout(right_layout, stretch=1)
        self.setLayout(main_layout)
        self.load_users_data()

    def load_users_data(self):
        users = airtable_api.get_all_users()
        self.users_table_widget.setRowCount(0)
        for row_idx, user_data in enumerate(users):
            self.users_table_widget.insertRow(row_idx)
            u_item = QTableWidgetItem(user_data.get("Username", "N/A"))
            r_item = QTableWidgetItem(user_data.get("Role", "N/A"))
            u_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            r_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.users_table_widget.setItem(row_idx, 0, u_item)
            self.users_table_widget.setItem(row_idx, 1, r_item)

    def handle_create_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combobox.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "All fields must be filled.")
            return

        record = airtable_api.add_new_user(username, password, role)
        if record:
            QMessageBox.information(self, "Success", f"Account '{username}' registered live.")
            self.username_input.clear()
            self.password_input.clear()
            self.load_users_data()


# ----------------------------------------------------
# 3. CENTRALISED NAVIGATION CONTROLLER (App Router)
# ----------------------------------------------------
class MainApplicationRouter(QStackedWidget):
    def __init__(self):
        super().__init__()

        # Instantiate child views
        self.login_page = LoginPage(on_login_success=self.navigate_on_login)
        self.admin_page = UserManagementPage(on_logout=self.navigate_to_logout)

        # Add views into the stack deck
        self.addWidget(self.login_page)  # Index 0
        self.addWidget(self.admin_page)  # Index 1

        # Configure application canvas size
        self.resize(800, 500)
        self.setWindowTitle("Medical Clinic Management Infrastructure")

    def navigate_on_login(self, role):
        if role == "Clinic administrator":
            self.admin_page.load_users_data()  # Pull fresh table state
            self.setCurrentIndex(1)  # Swap screen view smoothly to Dashboard

    def navigate_to_logout(self):
        self.login_page.username_input.clear()
        self.login_page.password_input.clear()
        self.setCurrentIndex(0)  # Bounce back to login screen safely


# Main initialization loop execution sequence
if __name__ == "__main__":
    app = QApplication(sys.argv)
    router = MainApplicationRouter()
    router.show()
    sys.exit(app.exec_())