import os
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QFrame,
    QApplication, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
from pyairtable import Api
from dotenv import load_dotenv
import config

# Resolve and load environment parameters from tests sequence path securely
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, 'tests', '.env')
load_dotenv(env_path)


def fetch_low_stock_medicines():
    """ Connects securely to the Airtable instance using sanitized credentials """
    try:
        raw_token = os.getenv('AIRTABLE_TOKEN') or config.AIRTABLE_TOKEN
        raw_base_id = os.getenv('BASE_ID') or config.BASE_ID

        if not raw_token or not raw_base_id:
            print(f"❌ Error: Could not find Airtable credentials in: {env_path}")
            return []

        clean_token = str(raw_token).replace('"', '').replace("'", "").strip()
        clean_base_id = str(raw_base_id).replace('"', '').replace("'", "").strip()

        api = Api(clean_token)
        catalog_table = api.table(clean_base_id, 'Medicines Catalog')

        records = catalog_table.all()
        low_stock_list = []

        for record in records:
            fields = record.get('fields', {})

            try:
                min_required = int(float(fields.get('Minimum Required', 0)))
            except (ValueError, TypeError):
                min_required = 0

            try:
                total_valid = int(float(fields.get('Total Valid Quantity', 0)))
            except (ValueError, TypeError):
                total_valid = 0

            if total_valid < min_required:
                raw_barcode = fields.get('Barcode', 'Unknown')
                if isinstance(raw_barcode, list):
                    raw_barcode = raw_barcode[0]
                elif isinstance(raw_barcode, dict):
                    raw_barcode = raw_barcode.get('text', 'Unknown')

                raw_name = fields.get('Name', 'Unknown')
                if isinstance(raw_name, list): raw_name = raw_name[0]

                category = fields.get('Category / Use', 'General Medicine')
                if isinstance(category, list): category = category[0]

                strength = fields.get('Strength', 'N/A')
                if isinstance(strength, list): strength = strength[0]

                low_stock_list.append({
                    'Barcode': str(raw_barcode).strip(),
                    'Name': str(raw_name).strip(),
                    'Category': str(category).strip(),
                    'Strength': str(strength).strip(),
                    'Quantity': total_valid,
                    'Threshold': min_required
                })

        return low_stock_list

    except Exception as e:
        print(f"\n❌ Airtable Catalog Fetch Exception: {e}\n")
        return []


class LowStockReportPage(QWidget):
    """
    Low-stock report displayed inside the application's main screen.
    The original report data logic is preserved.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.init_ui()

    def _make_scroll_area(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }

            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 14px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 35px;
                border-radius: 7px;
            }

            QScrollBar:horizontal {
                border: none;
                background: #F1F5F9;
                height: 14px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                min-width: 35px;
                border-radius: 7px;
            }
        """)
        scroll.setWidget(widget)
        return scroll

    def init_ui(self):
        self.setStyleSheet(
            "background-color: #F8FAFC; font-family: 'Segoe UI';"
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        page_content = QWidget()
        page_content.setMinimumHeight(520)

        main_layout = QVBoxLayout(page_content)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        header_layout = QHBoxLayout()

        header_lbl = QLabel("Low Stock Report")
        header_lbl.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #4F46E5;
            border: none;
        """)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                border: none;
                padding: 6px 14px;
            }

            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_report)

        close_btn = QPushButton("Menu")
        close_btn.setMinimumHeight(36)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                border: 1px solid #CBD5E1;
                padding: 6px 14px;
            }

            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """)
        close_btn.clicked.connect(self.handle_back)

        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        header_layout.addWidget(close_btn)
        card_layout.addLayout(header_layout)

        self.stats_lbl = QLabel("Total Low Stock Items: 0")
        self.stats_lbl.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #EF4444;
            border: none;
        """)
        card_layout.addWidget(self.stats_lbl)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(5)
        self.report_table.setHorizontalHeaderLabels([
            "Medicine Name",
            "Category / Use",
            "Strength",
            "Available Qty",
            "Threshold"
        ])
        self.report_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.report_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.report_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.report_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.report_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.report_table.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.report_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
                color: #1E293B;
            }

            QHeaderView::section {
                background-color: #F8FAFC;
                font-weight: bold;
                color: #475569;
                padding: 7px;
                font-size: 13px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }

            QTableWidget::item {
                padding: 7px;
                border-bottom: 1px solid #F1F5F9;
            }

            QTableWidget::item:selected {
                background-color: #EEF2FF;
                color: #4F46E5;
                font-weight: bold;
            }

            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 14px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 35px;
                border-radius: 7px;
            }

            QScrollBar:horizontal {
                border: none;
                background: #F1F5F9;
                height: 14px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                min-width: 35px;
                border-radius: 7px;
            }
        """)

        header = self.report_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.report_table.verticalHeader().setDefaultSectionSize(36)

        card_layout.addWidget(self.report_table)
        main_layout.addWidget(card)

        outer_layout.addWidget(self._make_scroll_area(page_content))

    def refresh_report(self):
        data = fetch_low_stock_medicines()
        self.stats_lbl.setText(
            f"Total Low Stock Items: {len(data)}"
        )

        self.report_table.setRowCount(len(data))

        for idx, item in enumerate(data):
            name_cell = QTableWidgetItem(item["Name"])
            category_cell = QTableWidgetItem(item["Category"])
            strength_cell = QTableWidgetItem(item["Strength"])
            quantity_cell = QTableWidgetItem(str(item["Quantity"]))
            threshold_cell = QTableWidgetItem(str(item["Threshold"]))

            quantity_cell.setTextAlignment(Qt.AlignCenter)
            threshold_cell.setTextAlignment(Qt.AlignCenter)

            self.report_table.setItem(idx, 0, name_cell)
            self.report_table.setItem(idx, 1, category_cell)
            self.report_table.setItem(idx, 2, strength_cell)
            self.report_table.setItem(idx, 3, quantity_cell)
            self.report_table.setItem(idx, 4, threshold_cell)

    def handle_back(self):
        if self.on_back_to_menu is not None:
            self.on_back_to_menu()

    def showEvent(self, event):
        self.refresh_report()
        super().showEvent(event)


def show_low_stock_table(parent=None, on_back_to_menu=None):
    return LowStockReportPage(
        parent=parent,
        on_back_to_menu=on_back_to_menu
    )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    show_low_stock_table()
    sys.exit(app.exec_())