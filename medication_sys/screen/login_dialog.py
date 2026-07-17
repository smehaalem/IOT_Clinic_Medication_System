import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QApplication
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


def make_dialog_kiosk_safe(dialog):
    flags = dialog.windowFlags()
    flags |= Qt.Dialog
    flags |= Qt.WindowStaysOnTopHint
    flags &= ~Qt.WindowMinimizeButtonHint
    flags &= ~Qt.WindowMaximizeButtonHint
    dialog.setWindowFlags(flags)
    dialog.setWindowModality(Qt.ApplicationModal)


def keep_dialog_visible(dialog):
    try:
        dialog.showNormal()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        pass


def show_safe_message(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    make_dialog_kiosk_safe(box)
    QTimer.singleShot(0, lambda: keep_dialog_visible(box))
    return box.exec_()


class QuickLoginDialog(QDialog):
    """
    Unified Multi-Stage Security Gate.

    Offline behavior:
    - When internet exists, users are loaded from Airtable and cached in SQLite.
    - When internet is unavailable, login uses the cached users from SQLite.
    - If the cache is empty, the user is asked to connect once to build the local cache.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.authenticated_user = None
        self.is_manager_phase = False
        self.matched_user_record = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Verification")
        self.setFixedSize(300, 280)
        make_dialog_kiosk_safe(self)

        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel {
                color: #1E293B;
                font-size: 11px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                font-size: 11px;
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1px solid #4F46E5;
                background-color: #F5F3FF;
                font-weight: bold;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(6)

        self.title_lbl = QLabel("Security Gate")
        self.title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #4F46E5; margin-bottom: 2px;"
        )
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title_lbl)

        self.main_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setMinimumHeight(28)
        self.main_layout.addWidget(self.username_input)

        self.pin_lbl = QLabel("PIN Code")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("****")
        self.pin_input.setMinimumHeight(28)
        self.main_layout.addWidget(self.pin_lbl)
        self.main_layout.addWidget(self.pin_input)

        self.pass_lbl = QLabel("Manager Password")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter manager password")
        self.password_input.setMinimumHeight(28)

        self.main_layout.addWidget(self.pass_lbl)
        self.main_layout.addWidget(self.password_input)

        self.pass_lbl.hide()
        self.password_input.hide()

        self.verify_btn = QPushButton("Verify Identity")
        self.verify_btn.setMinimumHeight(34)
        self.verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                border: none;
                margin-top: 4px;
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        self.verify_btn.clicked.connect(self.process_auth_submission)
        self.main_layout.addWidget(self.verify_btn)

        self.username_input.setFocus()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, lambda: keep_dialog_visible(self))
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.move_to_upper_position)

    def move_to_upper_position(self):
        try:
            parent = self.parent()
            if parent is not None:
                top_left = parent.mapToGlobal(parent.rect().topLeft())
                x = top_left.x() + max(0, (parent.width() - self.width()) // 2)
                y = top_left.y() + 35
            else:
                screen = QApplication.primaryScreen().availableGeometry()
                x = screen.x() + max(0, (screen.width() - self.width()) // 2)
                y = screen.y() + 35
            self.move(x, y)
        except Exception:
            pass

    def _load_users_for_login(self):
        """Load users from Airtable if online, otherwise from SQLite cache."""
        try:
            all_users = airtable_api.get_all_users()
        except Exception as exc:
            show_safe_message(
                self,
                QMessageBox.Critical,
                "Database Error",
                f"Could not load users from cloud or local cache:\n{str(exc)}"
            )
            return None

        if all_users:
            return all_users

        cloud_online = False
        try:
            cloud_online = airtable_api.is_cloud_online()
        except Exception:
            cloud_online = False

        if not cloud_online:
            show_safe_message(
                self,
                QMessageBox.Critical,
                "Offline Login Not Ready",
                "No internet connection was detected, and no cached users were found.\n\n"
                "Connect the system to the internet once and open Medicine Stock to cache System_Users locally. "
                "After that, login will work offline."
            )
        else:
            show_safe_message(
                self,
                QMessageBox.Critical,
                "Access Denied",
                "No users were found in the cloud or local cache."
            )

        return None

    def process_auth_submission(self):
        un = self.username_input.text().strip()
        if not un:
            show_safe_message(self, QMessageBox.Warning, "Input Error", "Username field cannot be left blank.")
            return

        if self.is_manager_phase:
            pwd = self.password_input.text().strip()
            if not pwd:
                show_safe_message(self, QMessageBox.Warning, "Input Error", "Manager Password field cannot be left blank.")
                return

            db_pass = str(self.matched_user_record.get("Password", "")).strip().split(".")[0]
            if db_pass == pwd:
                self.authenticated_user = self.matched_user_record
                self.accept()
            else:
                show_safe_message(self, QMessageBox.Critical, "Access Denied", "Incorrect Manager security password validation.")
            return

        pin = self.pin_input.text().strip()
        if not pin:
            show_safe_message(self, QMessageBox.Warning, "Input Error", "PIN field cannot be left blank.")
            return

        all_users = self._load_users_for_login()
        if all_users is None:
            return

        user_match = None

        for u in all_users:
            db_user = str(u.get("Username", "")).strip()
            db_pin_raw = str(u.get("PIN Code", "")).strip()
            db_pin = db_pin_raw.split(".")[0] if "." in db_pin_raw else db_pin_raw

            if db_user.lower() == un.lower() and db_pin == pin:
                user_match = u
                break

        if not user_match:
            show_safe_message(self, QMessageBox.Critical, "Access Denied", "Incorrect Username or numeric PIN Code.")
            return

        role_val = user_match.get("Role", "User")
        if isinstance(role_val, list):
            role_val = role_val[0] if role_val else "User"

        user_role = str(role_val).strip().lower()

        if user_role in ("maneger", "manager"):
            self.is_manager_phase = True
            self.matched_user_record = user_match

            self.pin_lbl.hide()
            self.pin_input.hide()

            self.pass_lbl.show()
            self.password_input.show()

            self.username_input.setReadOnly(True)
            self.username_input.setStyleSheet("""
                padding: 5px;
                border: 1px solid #E2E8F0;
                border-radius: 5px;
                font-size: 11px;
                background-color: #F1F5F9;
                color: #64748B;
                font-weight: 500;
            """)

            self.password_input.setFocus()
        else:
            self.authenticated_user = user_match
            self.accept()
