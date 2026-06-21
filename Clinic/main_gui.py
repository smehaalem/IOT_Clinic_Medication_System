import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
from PyQt5.QtGui import QFont, QCursor
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
        # התאמת רקע עדין ומודרני למסך כולו
        self.setStyleSheet("background-color: #F8FAFC;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)  # שליטה מדויקת בריווחים באמצעות מרווחים מוגדרים

        # כותרת המסך - שימוש בסטייל מודרני, צבע כהה ופונט Segoe UI
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

        # כפתור עבור מטופל חדש - סגנון אינדיגו מודרני עם פינות מעוגלות ואפקטים
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
            QPushButton:hover {
                background-color: #4338CA;
            }
            QPushButton:pressed {
                background-color: #3730A3;
            }
        """)
        btn_new.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        # כפתור עבור מטופל חוזר - סגנון אפור-צהבהב/כחול כהה (Slate) ליצירת היררכיה חזותית
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
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #1E293B;
            }
        """)
        btn_checkin.clicked.connect(self.go_to_checkin)

        # הוספת האלמנטים למסך עם המרווחים המעודכנים
        layout.addWidget(title)
        layout.addSpacing(40)
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

        # הגדרת פונט גלובלי לחלון
        self.setStyleSheet("QWidget { font-family: 'Segoe UI'; }")

        self.stack = QStackedWidget(self)

        # Initialize screens and pass the stack reference for navigation
        self.main_menu = MainMenuScreen(self.stack)
        self.new_patient = NewPatientScreen(self.stack)
        self.checkin = CheckinScreen(self.stack)

        # Add screens to stack
        self.stack.addWidget(self.main_menu)  # Index 0
        self.stack.addWidget(self.new_patient)  # Index 1
        self.stack.addWidget(self.checkin)  # Index 2

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # ביטול שוליים מיותרים בראוטר הראשי
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        # Open in fullscreen/maximized mode
        self.showMaximized()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = KioskRouter()
    sys.exit(app.exec_())