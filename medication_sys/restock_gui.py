import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QMessageBox, QDateEdit, QSpinBox, QStackedWidget
)
from PyQt5.QtCore import QDate
import medication_service  # נשתמש בפונקציות הקיימות כאן


class RestockScreen(QStackedWidget):
    """
    Main controller for the Restock system.
    Index 0: Barcode entry.
    Index 1: Data entry form (Smart Fill enabled).
    """

    def __init__(self, on_back_to_menu=None):  # הוספנו את המשתנה כאן
        super().__init__()
        self.on_back_to_menu = on_back_to_menu  # שומרים אותו לשימוש בכפתור

        # Screen 0: Initial Barcode Scan
        self.scan_page = QWidget()
        self.init_scan_page()
        self.addWidget(self.scan_page)

        # Screen 1: Data Entry Form
        self.form_page = QWidget()
        self.init_form_page()
        self.addWidget(self.form_page)

        self.setCurrentIndex(0)
        self.setWindowTitle("Inventory Restock System")
        self.resize(400, 500)

    def init_scan_page(self):
        layout = QVBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode or enter manually...")
        btn = QPushButton("Search Medication")
        btn.clicked.connect(self.check_barcode)

        layout.addWidget(self.barcode_input)
        layout.addWidget(btn)

        # --- הוספת כפתור החזרה ---
        back_btn = QPushButton("⬅️ Return to Menu")
        back_btn.setStyleSheet(
            "background-color: transparent; color: #718096; border: none; font-weight: bold; text-decoration: underline; margin-top: 20px;")
        if self.on_back_to_menu:
            back_btn.clicked.connect(self.on_back_to_menu)
        layout.addWidget(back_btn)
        # ------------------------

        self.scan_page.setLayout(layout)

    def init_form_page(self):
        layout = QVBoxLayout()
        self.form = QFormLayout()

        self.name_input = QLineEdit()
        self.ingredient_input = QLineEdit()
        self.dosage_input = QLineEdit()
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate())
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 1000)
        self.batch_input = QLineEdit()

        self.form.addRow("Medicine Name:", self.name_input)
        self.form.addRow("Active Ingredient:", self.ingredient_input)
        self.form.addRow("Dosage:", self.dosage_input)
        self.form.addRow("Expiry Date:", self.expiry_input)
        self.form.addRow("Quantity:", self.quantity_input)
        self.form.addRow("Batch:", self.batch_input)

        layout.addLayout(self.form)
        self.save_btn = QPushButton("Save to Inventory")
        self.save_btn.clicked.connect(self.save_medication)
        layout.addWidget(self.save_btn)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.setCurrentIndex(0))
        layout.addWidget(back_btn)

        self.form_page.setLayout(layout)

    def check_barcode(self):
        """Uses the existing service to check if barcode exists."""
        barcode = self.barcode_input.text().strip()
        if not barcode:
            QMessageBox.warning(self, "Error", "Please enter a barcode.")
            return

        # שימוש בפונקציה מהקובץ ששלחת לי
        existing_records = medication_service.airtable_api.get_all_medications_by_barcode(barcode)

        if existing_records:
            # Smart Fill: Get data from the first existing record
            fields = existing_records[0].get('fields', {})
            self.name_input.setText(fields.get('Medicine Name', ''))
            self.name_input.setEnabled(False)
            self.ingredient_input.setText(fields.get('Active Ingredient', ''))
            self.ingredient_input.setEnabled(False)
            self.dosage_input.setText(fields.get('Dosage', ''))
            self.dosage_input.setEnabled(False)
        else:
            # New Medicine: Enable all fields
            self.name_input.setEnabled(True)
            self.ingredient_input.setEnabled(True)
            self.dosage_input.setEnabled(True)

        self.setCurrentIndex(1)

    def save_medication(self):
        """Calls your existing restock_medication function."""
        try:
            success = medication_service.restock_medication(
                barcode=self.barcode_input.text().strip(),
                medicine_name=self.name_input.text().strip(),
                active_ingredient=self.ingredient_input.text().strip(),
                dosage=self.dosage_input.text().strip(),
                expiry_date=self.expiry_input.date().toString("yyyy-MM-dd"),
                pills_to_add=self.quantity_input.value(),
                batch_number=self.batch_input.text().strip(),
                staff_name="Inventory Staff"  # תוכלי לשנות לפי הצורך
            )

            if success:
                QMessageBox.information(self, "Success", "Inventory updated successfully.")
                self.setCurrentIndex(0)
            else:
                QMessageBox.critical(self, "Error", "Failed to save to database.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"System error: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RestockScreen()
    window.show()
    sys.exit(app.exec_())