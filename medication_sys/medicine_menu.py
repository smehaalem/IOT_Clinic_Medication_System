import sys
import os
from datetime import datetime

# Updated path resolution to include both project root and Clinic subsystem paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
clinic_dir = os.path.join(root_dir, 'Clinic')

if root_dir not in sys.path:
    sys.path.append(root_dir)
if clinic_dir not in sys.path:
    sys.path.append(clinic_dir)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QDialog, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

# Sub-screen imports
from screen.login_dialog import QuickLoginDialog
from screen.admin_page import UserManagementPage
from screen.stock_page import MedicationManagementPage
from screen.dispense_page import DispenseMedicationPage
from screen.inventory_view_page import InventoryViewPage

from inventory_check import show_low_stock_table
import tkinter as tk

# Import KioskRouter from Clinic.kiosk_main
from Clinic.kiosk_main import KioskRouter


class MedicineSystemApp(QWidget):
    """ Main Clinic Application Dashboard with Dynamic Role-Based Button Scaling """

    def __init__(self):
        super().__init__()
        self.resize(950, 650)
        self.setWindowTitle("Clinic Management System")
        self.setStyleSheet("QWidget { font-family: 'Segoe UI'; }")

        # Session tracking keys for centralized security context
        self.authenticated_user_id = None
        self.authenticated_user_role = "User"
        self.authenticated_user_name = "System User"

        self.stack = QStackedWidget(self)
        self.build_main_menu_screen()  # Registered at launch

        # Safely add child screens to the stack framework core
        self.admin_page = UserManagementPage(on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.admin_page)

        self.med_management_page = MedicationManagementPage(on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.med_management_page)

        self.dispense_page = DispenseMedicationPage(on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.dispense_page)

        self.inventory_view_page = InventoryViewPage(self, on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.inventory_view_page)

        # Seamless Integration: Embed KioskRouter inside the framework stack
        self.kiosk_router_page = KioskRouter(on_back_to_main=lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.kiosk_router_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        # Explicit reference tracking the dynamic sub-menu widget container
        self.sub_menu_widget = None

    def build_main_menu_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(25)

        title = QLabel("Clinic Main Menu")
        title.setStyleSheet("font-size: 34px; font-weight: bold; color: #0F172A; margin-bottom: 15px;")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        med_btn = QPushButton("💊 Medicine Stock (Storage)")
        med_btn.setFixedSize(440, 80)
        med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        med_btn.setStyleSheet(self.get_large_menu_button_style("#4F46E5", "#4338CA"))

        med_btn.clicked.connect(self.handle_centralized_kiosk_login)
        layout.addWidget(med_btn, alignment=Qt.AlignCenter)

        patient_btn = QPushButton("👥 Patient Kiosk (Check-In)")
        patient_btn.setFixedSize(440, 80)
        patient_btn.setCursor(QCursor(Qt.PointingHandCursor))
        patient_btn.setStyleSheet(self.get_large_menu_button_style("#475569", "#334155"))
        patient_btn.clicked.connect(self.open_patient_kiosk)
        layout.addWidget(patient_btn, alignment=Qt.AlignCenter)

        self.stack.addWidget(page)

    def handle_centralized_kiosk_login(self):
        """ Enforces a single dynamic login window context upon entering parameters """
        dialog = QuickLoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            logged_in_user = dialog.authenticated_user

            # Extract active system privileges safely
            role_val = logged_in_user.get("Role", "User")
            if isinstance(role_val, list):
                role_val = role_val[0] if role_val else "User"
            user_role = str(role_val).strip().lower()

            # Keep global session cache warm and configured
            self.authenticated_user_id = logged_in_user.get("record_id") or logged_in_user.get("id")
            self.authenticated_user_role = user_role
            self.authenticated_user_name = logged_in_user.get("Full Name", logged_in_user.get("Username", "Staff Member"))

            # Build and switch layout cleanly based on verified parameters
            self.build_medicine_sub_menu()

    def open_patient_kiosk(self):
        self.stack.setCurrentWidget(self.kiosk_router_page)

    def build_medicine_sub_menu(self):
        """ Dynamically builds and replaces Index 1 widget inside the stack using object mappings """
        if self.sub_menu_widget:
            self.stack.removeWidget(self.sub_menu_widget)
            self.sub_menu_widget.deleteLater()

        self.sub_menu_widget = QWidget()
        self.sub_menu_widget.setStyleSheet("background-color: #FFFFFF;")
        layout = QVBoxLayout(self.sub_menu_widget)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Medicine Operations")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #1E293B; margin-bottom: 20px;")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # Scale layout button sizes responsively based on privilege signatures
        if self.authenticated_user_role == "maneger":
            btn_width, btn_height = 440, 68
            layout.setSpacing(14)
        else:
            btn_width, btn_height = 490, 82
            layout.setSpacing(20)

        # 1. Add Medicine Button
        add_med_btn = QPushButton("➕ Add New Medicine")
        add_med_btn.setFixedSize(btn_width, btn_height)
        add_med_btn.setStyleSheet(self.get_large_menu_button_style("#0D9488", "#0F766E"))
        add_med_btn.clicked.connect(self.direct_open_add_medicine)
        layout.addWidget(add_med_btn, alignment=Qt.AlignCenter)

        # 2. Dispense Button
        dispense_btn = QPushButton("📦 Give Medicine (Dispense)")
        dispense_btn.setFixedSize(btn_width, btn_height)
        dispense_btn.setStyleSheet(self.get_large_menu_button_style("#EF4444", "#DC2626"))
        dispense_btn.clicked.connect(self.direct_open_dispense)
        layout.addWidget(dispense_btn, alignment=Qt.AlignCenter)

        # 3. View Stock Button
        view_stock_btn = QPushButton("📋 View Active Stock")
        view_stock_btn.setFixedSize(btn_width, btn_height)
        view_stock_btn.setStyleSheet(self.get_large_menu_button_style("#3B82F6", "#2563EB"))
        view_stock_btn.clicked.connect(self.direct_open_inventory_browser)
        layout.addWidget(view_stock_btn, alignment=Qt.AlignCenter)

        # 4. Low Stock Button
        low_stock_btn = QPushButton("⚠️ Low Stock Report")
        low_stock_btn.setFixedSize(btn_width, btn_height)
        low_stock_btn.setStyleSheet(self.get_large_menu_button_style("#8B5CF6", "#7C3AED"))
        low_stock_btn.clicked.connect(self.launch_low_stock_report)
        layout.addWidget(low_stock_btn, alignment=Qt.AlignCenter)

        # 5. Manager Portal Button (Appended strictly only if the user role is authorized)
        if self.authenticated_user_role == "maneger":
            manager_btn = QPushButton("🔑 Manager Portal")
            manager_btn.setFixedSize(btn_width, btn_height)
            manager_btn.setStyleSheet(self.get_large_menu_button_style("#D97706", "#B45309"))
            manager_btn.clicked.connect(self.direct_open_manager_portal)
            layout.addWidget(manager_btn, alignment=Qt.AlignCenter)

        # Logout Button
        back_btn = QPushButton("⬅️ Log Out & Go Back")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #64748B; border: none; font-weight: bold; font-size: 16px; text-decoration: underline; margin-top: 15px;}
            QPushButton:hover { color: #475569; }
        """)
        back_btn.clicked.connect(self.secure_session_logout)
        layout.addWidget(back_btn, alignment=Qt.AlignCenter)

        self.stack.insertWidget(1, self.sub_menu_widget)
        self.stack.setCurrentWidget(self.sub_menu_widget)

    # =====================================================================
    # 🔓 SECURE DIRECT WORKSPACE NAVIGATION (Uses exact widget references)
    # =====================================================================
    def direct_open_add_medicine(self):
        self.med_management_page.set_current_user(self.authenticated_user_id)
        self.med_management_page.clear_all_fields()
        self.stack.setCurrentWidget(self.med_management_page)

    def direct_open_dispense(self):
        self.dispense_page.clear_page()
        self.dispense_page.set_user_session(self.authenticated_user_role, self.authenticated_user_name)
        self.stack.setCurrentWidget(self.dispense_page)

    def direct_open_inventory_browser(self):
        self.inventory_view_page.refresh_inventory_data()
        self.stack.setCurrentWidget(self.inventory_view_page)

    def direct_open_manager_portal(self):
        if self.authenticated_user_role == "maneger":
            self.admin_page.load_users_data()
            self.stack.setCurrentWidget(self.admin_page)
        else:
            QMessageBox.critical(self, "Access Denied ❌",
                                 f"Only verified 'Maneger' accounts can access administration settings.\nYour active role signature: {self.authenticated_user_role.upper()}")

    def return_to_sub_menu(self):
        """ Safe callback returning navigation directly back to the active sub-menu frame context """
        if self.sub_menu_widget:
            self.stack.setCurrentWidget(self.sub_menu_widget)
        else:
            self.stack.setCurrentIndex(0)

    def secure_session_logout(self):
        """ Wipes all current user session contexts to restore a completely generic dashboard state """
        self.authenticated_user_id = None
        self.authenticated_user_role = "User"
        self.authenticated_user_name = "System User"
        self.stack.setCurrentIndex(0)

    def get_large_menu_button_style(self, bg, press_bg):
        return f"""
            QPushButton {{
                background-color: {bg}; color: white;
                font-size: 18px; font-weight: bold;
                border-radius: 14px; border: none;
            }}
            QPushButton:pressed {{ background-color: {press_bg}; }}
        """

    def launch_low_stock_report(self):
        root = tk.Tk()
        root.withdraw()
        show_low_stock_table()
        root.mainloop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineSystemApp()
    window.show()
    sys.exit(app.exec_())