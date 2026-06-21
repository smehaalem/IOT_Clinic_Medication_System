from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSpinBox, QMessageBox, QHBoxLayout, QApplication, QStackedWidget, QLineEdit
)
import sys
import medication_service


class ScanScreen(QWidget):
    """Screen 1: Waiting for barcode scan or manual entry."""

    def __init__(self, on_barcode_scanned, on_back_to_menu=None): # הוספנו כאן
        super().__init__()
        self.on_barcode_scanned = on_barcode_scanned
        self.on_back_to_menu = on_back_to_menu
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Please scan or enter barcode")
        self.label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.label)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter barcode manually...")
        layout.addWidget(self.input)

        btn = QPushButton("Search Medication")
        btn.clicked.connect(lambda: self.on_barcode_scanned(self.input.text().strip()))
        layout.addWidget(btn)

        # --- הוספת כפתור החזרה ---
        back_btn = QPushButton("⬅️ Return to Menu")
        back_btn.setStyleSheet("background-color: transparent; color: #718096; border: none; font-weight: bold; text-decoration: underline; margin-top: 20px;")
        if self.on_back_to_menu:
            back_btn.clicked.connect(self.on_back_to_menu)
        layout.addWidget(back_btn)
        # ------------------------

        self.setLayout(layout)


class BatchSelectionScreen(QWidget):
    """Screen 2: Select a specific batch and dispensing amount."""

    def __init__(self, doctor_name, on_finish, on_another):
        super().__init__()
        self.doctor_name = doctor_name
        self.on_finish = on_finish  # Callback to return to main menu
        self.on_another = on_another  # Callback to return to scan screen
        self.barcode = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Available batches:")
        layout.addWidget(self.label)

        self.stock_list = QListWidget()
        layout.addWidget(self.stock_list)

        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Amount to dispense:"))
        self.spin_box = QSpinBox()
        self.spin_box.setRange(1, 100)
        amount_layout.addWidget(self.spin_box)
        layout.addLayout(amount_layout)

        self.btn_dispense = QPushButton("Confirm Dispense")
        self.btn_dispense.clicked.connect(self.handle_dispense)
        layout.addWidget(self.btn_dispense)

        # Navigation buttons for workflow control
        nav_layout = QHBoxLayout()
        self.btn_another = QPushButton("Dispense Another")
        self.btn_another.clicked.connect(self.on_another)
        nav_layout.addWidget(self.btn_another)

        self.btn_finish = QPushButton("Finish")  # 🔹 תוקן: עכשיו זה עם self.
        self.btn_finish.clicked.connect(self.on_finish)
        nav_layout.addWidget(self.btn_finish)

        layout.addLayout(nav_layout)

        self.setLayout(layout)
        self.current_stock_data = {}

    def load_data(self, barcode):
        """Fetches stock data for the scanned barcode."""
        self.barcode = barcode
        self.stock_list.clear()
        self.current_stock_data = medication_service.get_aggregated_stock_for_barcode(barcode)

        if not self.current_stock_data:
            QMessageBox.warning(self, "No Stock", "No available batches for this barcode.")
            return

        for expiry, d in self.current_stock_data.items():
            item = QListWidgetItem(f"Expiry: {expiry} | Available: {d['total_pills']}")
            item.setData(1, expiry)
            self.stock_list.addItem(item)

    def handle_dispense(self):
        """Processes the dispensing operation and logs history."""
        selected_item = self.stock_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Error", "Please select a batch first!")
            return

        expiry = selected_item.data(1)
        batch_info = self.current_stock_data[expiry]
        record_id = batch_info['record_ids'][0]['id']
        amount = self.spin_box.value()

        result = medication_service.dispense_medication_to_patient(
            self.barcode, record_id, amount, self.doctor_name
        )

        if result["success"]:
            QMessageBox.information(self, "Success", "Dispense completed successfully!")
            self.load_data(self.barcode)  # Refresh list after successful dispense
        else:
            QMessageBox.critical(self, "Error", result["message"])


class DispenseSystem(QStackedWidget):
    """
    Main Router that switches between ScanScreen and BatchSelectionScreen.
    """

    def __init__(self, on_back_to_menu=None): # הוספנו כאן
        super().__init__()
        # מעבירים את הפקודה למסך הסריקה
        self.scan_screen = ScanScreen(
            on_barcode_scanned=self.go_to_batch,
            on_back_to_menu=on_back_to_menu
        )
        self.batch_screen = BatchSelectionScreen(
            doctor_name="Dr. Levi",
            on_finish=lambda: print("Finish clicked - Close app or go home"),
            on_another=lambda: self.setCurrentIndex(0)
        )

        self.addWidget(self.scan_screen)
        self.addWidget(self.batch_screen)
        self.setCurrentIndex(0)

    def go_to_batch(self, barcode):
        if barcode:
            self.batch_screen.load_data(barcode)
            self.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Error", "Please enter a barcode")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    system = DispenseSystem()
    system.show()
    sys.exit(app.exec_())