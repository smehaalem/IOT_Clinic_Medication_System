import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt

# Import the refactored checkingui screen
from checkingui import CheckinScreen


class MainMenuScreen(QWidget):
    """ Simplified Patient Kiosk Welcome Screen """

    def __init__(self, stack, on_back_to_main=None):
        super().__init__()
        self.stack = stack
        self.on_back_to_main = on_back_to_main
        self.init_ui()

    def init_ui(self):
        # Force pure white background on the menu page widget
        self.setStyleSheet("background-color: #FFFFFF; border: none;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Large prominent main title
        title = QLabel("Welcome to the Clinic")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 36px;
                font-weight: bold;
                color: #0F172A;
            }
        """)

        # Basic and polite instruction subtitle
        subtitle = QLabel("Please tap the button below to check in:")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-family: 'Segoe UI'; font-size: 16px; color: #64748B; margin-bottom: 40px;")

        # Unified, ultra-bold, simple action button for patients
        btn_start = QPushButton("👋 Start Check-In")
        btn_start.setFixedSize(400, 90)
        btn_start.setCursor(QCursor(Qt.PointingHandCursor))
        btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                font-family: 'Segoe UI';
                font-size: 22px;
                font-weight: bold;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover { background-color: #4338CA; }
            QPushButton:pressed { background-color: #3730A3; }
        """)
        btn_start.clicked.connect(self.go_to_checkin)

        # Simplified staff dashboard exit button
        btn_exit_kiosk = QPushButton("🚪 Exit Kiosk")
        btn_exit_kiosk.setFixedSize(400, 55)
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

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(btn_start, alignment=Qt.AlignCenter)
        layout.addSpacing(40)
        layout.addWidget(btn_exit_kiosk, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def go_to_checkin(self):
        # Move index to the input form screen (Index 1)
        checkin_widget = self.stack.widget(1)
        if hasattr(checkin_widget, 'prepare_for_scan'):
            checkin_widget.prepare_for_scan()
        self.stack.setCurrentIndex(1)

    def exit_kiosk_context(self):
        """ Closes the kiosk router view and triggers wrapper dashboard callback """
        if self.on_back_to_main:
            self.on_back_to_main()  # Switches the stack index back to 0 (Main Menu)


class KioskRouter(QWidget):
    """ The Router that holds all screens using QStackedWidget """

    def __init__(self, on_back_to_main=None):
        super().__init__()
        self.setWindowTitle('Smart Clinic - Patient Kiosk')

        # Force pure white background globally across the router container and its internal stacks
        self.setStyleSheet("""
            KioskRouter { background-color: #FFFFFF; border: none; }
            QStackedWidget { background-color: #FFFFFF; border: none; }
        """)

        self.stack = QStackedWidget(self)

        self.main_menu = MainMenuScreen(self.stack, on_back_to_main=on_back_to_main)
        self.checkin = CheckinScreen(self.stack)

        self.stack.addWidget(self.main_menu)  # Index 0
        self.stack.addWidget(self.checkin)    # Index 1

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = KioskRouter()
    sys.exit(app.exec_())