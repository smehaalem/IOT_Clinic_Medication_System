import sys
import os
from datetime import datetime

# Path resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
clinic_dir = os.path.join(root_dir, 'Clinic')

if root_dir not in sys.path:
    sys.path.append(root_dir)
if clinic_dir not in sys.path:
    sys.path.append(clinic_dir)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QDialog, QApplication,
    QScrollArea, QSizePolicy, QInputDialog
)
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QCursor

# Sub-screen imports
from screen.login_dialog import QuickLoginDialog
from screen.admin_page import UserManagementPage
from screen.stock_page import MedicationManagementPage
from screen.dispense_page import DispenseMedicationPage
from screen.inventory_view_page import InventoryViewPage
from inventory_check import LowStockReportPage
import tkinter as tk
from Clinic.kiosk_main import KioskRouter
import airtable_api


# Developer-only password for closing the kiosk app.
# On the Raspberry Pi you can override it without editing code by running:
# export KIOSK_EXIT_PASSWORD=your_password
DEFAULT_EXIT_PASSWORD = os.getenv("KIOSK_EXIT_PASSWORD", "2468")


def make_dialog_kiosk_safe(dialog):
    flags = dialog.windowFlags()
    flags |= Qt.Dialog
    flags |= Qt.WindowStaysOnTopHint
    flags &= ~Qt.WindowMinimizeButtonHint
    flags &= ~Qt.WindowMaximizeButtonHint
    dialog.setWindowFlags(flags)
    dialog.setWindowModality(Qt.ApplicationModal)


def show_safe_message(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    make_dialog_kiosk_safe(box)
    QTimer.singleShot(0, lambda: keep_window_visible(box))
    return box.exec_()


def keep_window_visible(widget):
    try:
        widget.showNormal()
        widget.raise_()
        widget.activateWindow()
    except Exception:
        pass


class MedicineSystemApp(QWidget):
    """ Main Clinic Application Dashboard with Responsive Touch UI """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Clinic Management System")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("QWidget { font-family: 'Segoe UI'; }")

        # Closing the kiosk is protected. This flag becomes True only after
        # the developer password is entered correctly.
        self._allow_close = False

        # Full screen for Raspberry Pi touchscreen
        self.showFullScreen()

        self.authenticated_user_id = None
        self.authenticated_user_role = "User"
        self.authenticated_user_name = "System User"

        self.prepare_offline_cache()

        self.stack = QStackedWidget(self)
        self.build_main_menu_screen()

        # Add child screens
        self.admin_page = UserManagementPage(on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.admin_page)

        self.med_management_page = MedicationManagementPage(on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.med_management_page)

        self.dispense_page = DispenseMedicationPage(on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.dispense_page)

        self.inventory_view_page = InventoryViewPage(self, on_back_to_menu=self.return_to_sub_menu)
        self.stack.addWidget(self.inventory_view_page)

        self.low_stock_report_page = LowStockReportPage(
            self,
            on_back_to_menu=self.return_to_sub_menu
        )
        self.stack.addWidget(self.low_stock_report_page)

        self.kiosk_router_page = KioskRouter(on_back_to_main=lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.kiosk_router_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.sub_menu_widget = None


    def prepare_offline_cache(self):
        """
        Preload users and medicine stock from Airtable into SQLite while internet exists.
        This allows the Medicine Stock area to keep working later without internet.
        """
        try:
            if hasattr(airtable_api, "warm_up_offline_cache"):
                report = airtable_api.warm_up_offline_cache(sync_stock=True, sync_users=True)
                print(f"Offline cache warm-up report: {report}")
        except Exception as e:
            # Do not block the GUI if Airtable is unavailable.
            print(f"Offline cache warm-up skipped: {e}")

    def create_exit_button(self):
        exit_btn = QPushButton("X")
        exit_btn.setFixedSize(36, 36)
        exit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 18px;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        exit_btn.clicked.connect(self.request_secure_exit)
        return exit_btn

    def request_secure_exit(self):
        """Ask for the developer password before closing the kiosk app."""
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Developer Exit")
        dialog.setLabelText("Enter developer password to close the system:")
        dialog.setTextEchoMode(QLineEdit.Password)
        make_dialog_kiosk_safe(dialog)

        if dialog.exec_() != QDialog.Accepted:
            self._recover_fullscreen()
            return

        password = dialog.textValue()

        if password == DEFAULT_EXIT_PASSWORD:
            self._allow_close = True
            QApplication.quit()
        else:
            show_safe_message(
                self,
                QMessageBox.Warning,
                "Access Denied",
                "Incorrect password. The system will remain open."
            )
            self._recover_fullscreen()

    def closeEvent(self, event):
        """Protect OS/window-manager close actions such as Alt+F4 or title-bar X."""
        if self._allow_close:
            event.accept()
            return

        event.ignore()
        self.request_secure_exit()

    def changeEvent(self, event):
        """Prevent the kiosk from staying minimized and showing the desktop."""
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self._recover_fullscreen)
        super().changeEvent(event)

    def _recover_fullscreen(self):
        try:
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
            self.showFullScreen()
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def create_scrollable_page(self, inner_widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #FFFFFF; }")
        scroll.setWidget(inner_widget)
        return scroll

    def build_main_menu_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        exit_btn = self.create_exit_button()
        exit_btn.setParent(page)
        exit_btn.move(800 - 36 - 8, 8)
        exit_btn.raise_()

        layout = QVBoxLayout(page)

        # Keeps the window full screen, but moves the title/buttons higher
        layout.setContentsMargins(0, 120, 0, 0)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(20)
        center_layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Clinic Main Menu")
        title.setStyleSheet("font-size: 52px; font-weight: bold; color: #0F172A;")
        center_layout.addWidget(title, alignment=Qt.AlignCenter)

        med_btn = QPushButton("Medicine Stock")
        med_btn.setFixedSize(260, 50)
        med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        med_btn.setStyleSheet(self.get_large_menu_button_style("#4F46E5", "#4338CA"))
        med_btn.clicked.connect(self.handle_centralized_kiosk_login)
        center_layout.addWidget(med_btn, alignment=Qt.AlignCenter)

        patient_btn = QPushButton("Patient Check-In")
        patient_btn.setFixedSize(260, 50)
        patient_btn.setCursor(QCursor(Qt.PointingHandCursor))
        patient_btn.setStyleSheet(self.get_large_menu_button_style("#475569", "#334155"))
        patient_btn.clicked.connect(self.open_patient_kiosk)
        center_layout.addWidget(patient_btn, alignment=Qt.AlignCenter)

        layout.addWidget(center_widget, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.stack.addWidget(page)

    def build_medicine_sub_menu(self):
        if self.sub_menu_widget:
            self.stack.removeWidget(self.sub_menu_widget)
            self.sub_menu_widget.deleteLater()

        inner_widget = QWidget()
        inner_widget.setStyleSheet("background-color: #FFFFFF;")

        exit_btn = self.create_exit_button()
        exit_btn.setParent(inner_widget)
        exit_btn.move(800 - 36 - 8, 8)
        exit_btn.raise_()

        layout = QVBoxLayout(inner_widget)

        # Keep this page full screen and place the menu near the top for 800x480 landscape.
        layout.setContentsMargins(0, 45, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Medicine Operations")
        title.setStyleSheet("font-size: 46px; font-weight: bold; color: #1E293B;")
        center_layout.addWidget(title, alignment=Qt.AlignCenter)

        btn_width, btn_height = 300, 46

        btns = [
            ("Add New Medicine", self.direct_open_add_medicine, "#0D9488"),
            ("Give Medicine", self.direct_open_dispense, "#EF4444"),
            ("View Active Stock", self.direct_open_inventory_browser, "#3B82F6"),
            ("Low Stock Report", self.launch_low_stock_report, "#8B5CF6")
        ]

        if self.authenticated_user_role in ("maneger", "manager"):
            btns.append(("Manager Portal", self.direct_open_manager_portal, "#D97706"))

        for text, func, color in btns:
            btn = QPushButton(text)
            btn.setFixedSize(btn_width, btn_height)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(self.get_large_menu_button_style(color, color))
            btn.clicked.connect(func)
            center_layout.addWidget(btn, alignment=Qt.AlignCenter)

        back_btn = QPushButton("Log Out & Go Back")
        back_btn.setStyleSheet(
            "QPushButton { background: none; color: #64748B; border: none; "
            "font-weight: bold; font-size: 11px; text-decoration: underline; margin-top: 5px; }"
        )
        back_btn.clicked.connect(self.secure_session_logout)
        center_layout.addWidget(back_btn, alignment=Qt.AlignCenter)

        layout.addWidget(center_widget, alignment=Qt.AlignHCenter | Qt.AlignTop)

        self.sub_menu_widget = self.create_scrollable_page(inner_widget)
        self.stack.insertWidget(1, self.sub_menu_widget)
        self.stack.setCurrentWidget(self.sub_menu_widget)

    def get_large_menu_button_style(self, bg, press_bg):
        return f"""
        QPushButton {{
            background-color: {bg};
            color: white;
            font-size: 28px;
            font-weight: bold;
            border-radius: 6px;
            border: none;
            padding: 3px;
        }}
        QPushButton:pressed {{
            background-color: {press_bg};
        }}
        """

    def _clean_text_value(self, value):
        """Return a clean string from Airtable values that may be plain text or lists."""
        if value is None:
            return ""
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value).strip()
        if text.lower() in ("none", "null", "nan"):
            return ""
        return text

    def _resolve_logged_in_full_name(self, logged_in_user):
        """Prefer the staff member's full name, but never leave Action By User as System User."""
        if not isinstance(logged_in_user, dict):
            return "Staff"

        # Main expected Airtable field, plus safe fallbacks in case the column name differs.
        possible_full_name_keys = (
            "Full Name", "FullName", "Name", "Staff Name",
            "Employee Name", "Display Name", "User Full Name"
        )

        for key in possible_full_name_keys:
            value = self._clean_text_value(logged_in_user.get(key))
            if value:
                return value

        # Last fallback: username, so history will still identify the user better than System User.
        username = self._clean_text_value(logged_in_user.get("Username"))
        return username or "Staff"

    def _apply_authenticated_session_to_pages(self):
        """Push the current login session into child pages before opening them."""
        if hasattr(self.med_management_page, "set_current_user"):
            self.med_management_page.set_current_user(self.authenticated_user_id)

        if hasattr(self.dispense_page, "set_user_session"):
            self.dispense_page.set_user_session(
                self.authenticated_user_role,
                self.authenticated_user_name,
                self.authenticated_user_name
            )

    def handle_centralized_kiosk_login(self):
        dialog = QuickLoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            logged_in_user = dialog.authenticated_user
            self.authenticated_user_id = logged_in_user.get("record_id")
            self.authenticated_user_role = self._clean_text_value(logged_in_user.get("Role")) or "User"
            self.authenticated_user_role = self.authenticated_user_role.lower()
            self.authenticated_user_name = self._resolve_logged_in_full_name(logged_in_user)

            # Pass the authenticated session into child pages so history/restock
            # records show the real staff member instead of the default System User.
            self._apply_authenticated_session_to_pages()
            print(f"Logged in staff: {self.authenticated_user_name} ({self.authenticated_user_role})")

            self.build_medicine_sub_menu()

    def open_patient_kiosk(self):
        self.stack.setCurrentWidget(self.kiosk_router_page)

    def direct_open_add_medicine(self):
        self._apply_authenticated_session_to_pages()
        self.stack.setCurrentWidget(self.med_management_page)

    def direct_open_dispense(self):
        self._apply_authenticated_session_to_pages()
        self.stack.setCurrentWidget(self.dispense_page)

    def direct_open_inventory_browser(self):
        self.stack.setCurrentWidget(self.inventory_view_page)

    def direct_open_manager_portal(self):
        self.stack.setCurrentWidget(self.admin_page)

    def return_to_sub_menu(self):
        if self.sub_menu_widget:
            self.stack.setCurrentWidget(self.sub_menu_widget)
        else:
            self.stack.setCurrentIndex(0)

    def secure_session_logout(self):
        self.stack.setCurrentIndex(0)


    def manual_sync_pending_changes(self):
        try:
            pending_before = airtable_api.get_pending_sync_count()
            if not airtable_api.is_cloud_online():
                show_safe_message(
                    self,
                    QMessageBox.Warning,
                    "Offline Mode",
                    f"No internet connection detected. Pending local operations: {pending_before}"
                )
                return

            pulled = airtable_api.refresh_local_stock_from_cloud()
            success, failed = airtable_api.sync_pending_operations()
            pending_after = airtable_api.get_pending_sync_count()

            show_safe_message(
                self,
                QMessageBox.Information,
                "Sync Complete",
                f"Uploaded operations: {success}\nStill pending/failed: {pending_after}\nCloud stock rows refreshed: {pulled}"
            )
        except Exception as e:
            show_safe_message(self, QMessageBox.Critical, "Sync Error", str(e))

    def launch_low_stock_report(self):
        self.low_stock_report_page.refresh_report()
        self.stack.setCurrentWidget(self.low_stock_report_page)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicineSystemApp()
    sys.exit(app.exec_())
