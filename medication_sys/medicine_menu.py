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

# Import the Kiosk Router from the sibling Clinic directory
from Clinic.main_gui import KioskRouter

class MedicineSystemApp(QWidget):
    """ Modern Dashboard Layout Navigation Core """
    def __init__(self):
        super().__init__()
        self.resize(920, 620)
        self.setWindowTitle("Clinic Operations Infrastructure")
        self.setStyleSheet("QWidget { font-family: 'Segoe UI'; }")

        self.stack = QStackedWidget(self)
        self.build_main_menu_screen()      # Index 0
        self.build_medicine_sub_menu()     # Index 1

        # Connect internal sub-pages to the Main Stack Core
        self.admin_page = UserManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.admin_page)  # Index 2

        self.med_management_page = MedicationManagementPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.med_management_page)  # Index 3

        self.dispense_page = DispenseMedicationPage(on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.dispense_page)  # Index 4

        self.inventory_view_page = InventoryViewPage(self, on_back_to_menu=lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.inventory_view_page)  # Index 5

        # Seamless Integration: Embed KioskRouter inside the existing main window stack framework
        # When closing/returning from kiosk, it natively switches the index back to the main dashboard (Index 0)
        self.kiosk_router_page = KioskRouter(on_back_to_main=lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.kiosk_router_page)  # Index 6

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

        # Patient Workspace button now cleanly transitions index context without popping extra system frames
        patient_btn = QPushButton("👥 Patient File Workspace")
        patient_btn.setCursor(QCursor(Qt.PointingHandCursor))
        patient_btn.setStyleSheet(self.get_menu_button_style("#475569", "#334155"))
        patient_btn.clicked.connect(self.open_patient_kiosk)
        layout.addWidget(patient_btn)

        self.stack.addWidget(page)

    def open_patient_kiosk(self):
        """ Smoothly transitions the stacked index layer into the embedded Kiosk subsystem """
        self.stack.setCurrentIndex(6)

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

        dispense_btn = QPushButton("📦 Dispense / Deduct Quantity")
        dispense_btn.setStyleSheet(self.get_menu_button_style("#EF4444", "#DC2626"))
        dispense_btn.clicked.connect(lambda: self.trigger_secure_action("Dispense Medicine"))
        layout.addWidget(dispense_btn)

        view_stock_btn = QPushButton("📋 Browse Active Inventory Stores")
        view_stock_btn.setStyleSheet(self.get_menu_button_style("#3B82F6", "#2563EB"))
        view_stock_btn.clicked.connect(self.open_inventory_browser)
        layout.addWidget(view_stock_btn)

        manager_btn = QPushButton("🔑 Manager Administration Portal")
        manager_btn.setStyleSheet(self.get_menu_button_style("#D97706", "#B45309"))
        manager_btn.clicked.connect(self.trigger_manager_portal)
        layout.addWidget(manager_btn)

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
            logged_in_user = dialog.authenticated_user

            username = logged_in_user.get("Username", "Unknown")
            user_rec_id = logged_in_user.get("record_id") or logged_in_user.get("id")
            full_name_val = logged_in_user.get("Full Name", username)

            role_val = logged_in_user.get("Role", "User")
            if isinstance(role_val, list):
                role_val = role_val[0] if role_val else "User"

            if action_name == "Add Medicine":
                self.med_management_page.set_current_user(user_rec_id)
                self.med_management_page.clear_all_fields()
                self.stack.setCurrentIndex(3)

            elif action_name == "Dispense Medicine":
                self.dispense_page.clear_page()
                self.dispense_page.set_user_session(role_val, full_name_val)
                self.stack.setCurrentIndex(4)

    def open_inventory_browser(self):
        dialog = QuickLoginDialog(self, require_password=False)
        if dialog.exec_() == QDialog.Accepted:
            self.inventory_view_page.refresh_inventory_data()
            self.stack.setCurrentIndex(5)

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
                QMessageBox.critical(self, "Security Error ❌", f"Only verified 'Maneger' roles can enter this panel. Your role is: {role_val}")

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