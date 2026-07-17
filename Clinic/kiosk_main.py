import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
)
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt

from checkingui import CheckinScreen
from add_patient_screen import AddPatientScreen


class MainMenuScreen(QWidget):
    """Patient kiosk welcome screen."""

    def __init__(self, stack, on_back_to_main=None):
        super().__init__()
        self.stack = stack
        self.on_back_to_main = on_back_to_main
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #FFFFFF; border: none;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("Welcome to the Clinic")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 34px;
                font-weight: bold;
                color: #0F172A;
            }
        """)

        subtitle = QLabel("Choose an action:")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-family: 'Segoe UI'; font-size: 16px; color: #64748B; margin-bottom: 18px;")

        btn_start = QPushButton("Start Check-In")
        btn_start.setFixedSize(310, 80)
        btn_start.setCursor(QCursor(Qt.PointingHandCursor))
        btn_start.setStyleSheet(self.primary_button_style())
        btn_start.clicked.connect(self.go_to_checkin)

        btn_add_patient = QPushButton("Add New Patient")
        btn_add_patient.setFixedSize(310, 80)
        btn_add_patient.setCursor(QCursor(Qt.PointingHandCursor))
        btn_add_patient.setStyleSheet(self.primary_button_style())
        btn_add_patient.clicked.connect(self.go_to_add_patient)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(22)
        actions_row.addWidget(btn_start, alignment=Qt.AlignCenter)
        actions_row.addWidget(btn_add_patient, alignment=Qt.AlignCenter)

        btn_exit_kiosk = QPushButton("Exit Kiosk")
        btn_exit_kiosk.setFixedSize(310, 48)
        btn_exit_kiosk.setCursor(QCursor(Qt.PointingHandCursor))
        btn_exit_kiosk.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748B;
                border: 2px dashed #CBD5E1;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 14px;
                border-radius: 12px;
            }
            QPushButton:hover {
                color: #0F172A;
                border: 2px solid #94A3B8;
                background-color: #F1F5F9;
            }
        """)
        btn_exit_kiosk.clicked.connect(self.exit_kiosk_context)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(14)
        layout.addLayout(actions_row)
        layout.addSpacing(28)
        layout.addWidget(btn_exit_kiosk, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.setLayout(layout)

    def primary_button_style(self):
        return """
            QPushButton {
                background-color: #4F46E5;
                color: white;
                font-family: 'Segoe UI';
                font-size: 20px;
                font-weight: bold;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover { background-color: #4338CA; }
            QPushButton:pressed { background-color: #3730A3; }
        """

    def go_to_checkin(self):
        checkin_widget = self.stack.widget(1)
        if hasattr(checkin_widget, "prepare_for_scan"):
            checkin_widget.prepare_for_scan()
        self.stack.setCurrentIndex(1)

    def go_to_add_patient(self):
        add_patient_widget = self.stack.widget(2)
        if hasattr(add_patient_widget, "prepare_for_add"):
            add_patient_widget.prepare_for_add()
        self.stack.setCurrentIndex(2)

    def exit_kiosk_context(self):
        if self.on_back_to_main:
            self.on_back_to_main()


class KioskRouter(QWidget):
    """Router that holds all patient kiosk screens."""

    def __init__(self, on_back_to_main=None):
        super().__init__()
        self.setWindowTitle("Smart Clinic - Patient Kiosk")
        self.setStyleSheet("""
            KioskRouter { background-color: #FFFFFF; border: none; }
            QStackedWidget { background-color: #FFFFFF; border: none; }
        """)

        self.stack = QStackedWidget(self)

        self.main_menu = MainMenuScreen(self.stack, on_back_to_main=on_back_to_main)
        self.checkin = CheckinScreen(self.stack)
        self.add_patient = AddPatientScreen(self.stack)

        self.stack.addWidget(self.main_menu)
        self.stack.addWidget(self.checkin)
        self.stack.addWidget(self.add_patient)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = KioskRouter()
    ex.resize(800, 480)
    ex.show()
    sys.exit(app.exec_())
