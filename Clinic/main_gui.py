import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Import the individual screens
from new_patient_gui import NewPatientScreen
from checkin_gui import CheckinScreen

class MainMenuScreen(QWidget):
    """ The Main Menu UI """
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Smart Clinic Kiosk")
        title.setFont(QFont("Arial", 30, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        # Button to register a new patient
        btn_new = QPushButton("New Patient (Print ID)")
        btn_new.setFixedSize(400, 100)
        btn_new.setFont(QFont("Arial", 18))
        btn_new.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        # Button for returning patients (barcode scan)
        btn_checkin = QPushButton("Returning Patient (Scan ID)")
        btn_checkin.setFixedSize(400, 100)
        btn_checkin.setFont(QFont("Arial", 18))
        btn_checkin.clicked.connect(self.go_to_checkin)

        layout.addWidget(title)
        layout.addSpacing(50)
        layout.addWidget(btn_new, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(btn_checkin, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def go_to_checkin(self):
        # Prepare the check-in screen (clear text and focus scanner input) before switching
        checkin_widget = self.stack.widget(2)
        checkin_widget.prepare_for_scan()
        self.stack.setCurrentIndex(2)

class KioskRouter(QWidget):
    """ The Router that holds all screens using QStackedWidget """
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Smart Clinic - Patient Kiosk')
        self.stack = QStackedWidget(self)

        # Initialize screens and pass the stack reference for navigation
        self.main_menu = MainMenuScreen(self.stack)
        self.new_patient = NewPatientScreen(self.stack)
        self.checkin = CheckinScreen(self.stack)

        # Add screens to stack
        self.stack.addWidget(self.main_menu)   # Index 0
        self.stack.addWidget(self.new_patient) # Index 1
        self.stack.addWidget(self.checkin)     # Index 2

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        # Open in fullscreen/maximized mode
        self.showMaximized()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = KioskRouter()
    sys.exit(app.exec_())