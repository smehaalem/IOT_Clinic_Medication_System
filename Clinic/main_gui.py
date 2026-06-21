import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt

# Import the individual screens
from new_patient_gui import NewPatientScreen
from checkin_gui import CheckinScreen


class MainMenuScreen(QWidget):
    """ The Main Menu UI """

    # Accept the on_back_to_main callback parameter
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

        title = QLabel("Smart Clinic Kiosk")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 32px;
                font-weight: bold;
                color: #0F172A;
            }
        """)

        btn_new = QPushButton("📝 New Patient (Print ID)")
        btn_new.setFixedSize(400, 85)
        btn_new.setCursor(QCursor(Qt.PointingHandCursor))
        btn_new.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                font-family: 'Segoe UI';
                font-size: 18px;
                font-weight: bold;
                border-radius: 14px;
                border: none;
            }
            QPushButton:hover { background-color: #4338CA; }
            QPushButton:pressed { background-color: #3730A3; }
        """)
        btn_new.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        btn_checkin = QPushButton("🔍 Returning Patient (Scan ID)")
        btn_checkin.setFixedSize(400, 85)
        btn_checkin.setCursor(QCursor(Qt.PointingHandCursor))
        btn_checkin.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: white;
                font-family: 'Segoe UI';
                font-size: 18px;
                font-weight: bold;
                border-radius: 14px;
                border: none;
            }
            QPushButton:hover { background-color: #334155; }
            QPushButton:pressed { background-color: #1E293B; }
        """)
        btn_checkin.clicked.connect(self.go_to_checkin)

        # New Return to App Launcher Dashboard Button
        btn_exit_kiosk = QPushButton("🚪 Return to System Dashboard")
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
                border-radius: 10px;
            }
            QPushButton:hover {
                color: #0F172A;
                border: 2px solid #94A3B8;
                background-color: #F1F5F9;
            }
        """)
        btn_exit_kiosk.clicked.connect(self.exit_kiosk_context)

        layout.addWidget(title)
        layout.addSpacing(40)
        layout.addWidget(btn_new, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(btn_checkin, alignment=Qt.AlignCenter)
        layout.addSpacing(35)
        layout.addWidget(btn_exit_kiosk, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def go_to_checkin(self):
        checkin_widget = self.stack.widget(2)
        checkin_widget.prepare_for_scan()
        self.stack.setCurrentIndex(2)

    def exit_kiosk_context(self):
        """ Closes the kiosk router view and triggers wrapper dashboard callback """
        if self.on_back_to_main:
            self.on_back_to_main()  # Switches the stack index back to 0 (Main Menu)


class KioskRouter(QWidget):
    """ The Router that holds all screens using QStackedWidget """

    def __init__(self, on_back_to_main=None):
        super().__init__()
        self.setWindowTitle('Smart Clinic - Patient Kiosk')

        # FIX: Force pure white background globally across the router container and its internal stacks
        self.setStyleSheet("""
            KioskRouter { background-color: #FFFFFF; border: none; }
            QStackedWidget { background-color: #FFFFFF; border: none; }
        """)

        self.stack = QStackedWidget(self)

        # Forward the parent application container callback reference down to menu layout
        self.main_menu = MainMenuScreen(self.stack, on_back_to_main=on_back_to_main)
        self.new_patient = NewPatientScreen(self.stack)
        self.checkin = CheckinScreen(self.stack)

        self.stack.addWidget(self.main_menu)  # Index 0
        self.stack.addWidget(self.new_patient)  # Index 1
        self.stack.addWidget(self.checkin)  # Index 2

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = KioskRouter()
    sys.exit(app.exec_())