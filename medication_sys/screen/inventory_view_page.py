# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
import airtable_api


class InventoryViewPage(QWidget):
    """
    Modern Clinic Inventory Browser using a clean multi-screen Stacked UI.
    Optimized with custom scrollbars and readable fonts.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)

        self.on_back_to_menu = on_back_to_menu
        self.all_cached_inventory = []

        # Internal stack for the directory and details screens
        self.internal_stack = QStackedWidget(self)

        self.init_directory_screen()  # Index 0
        self.init_details_screen()    # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

        # Initial data loading
        self.refresh_inventory_data()

    # =====================================================================
    # SCREEN 0: Main inventory directory
    # =====================================================================
    def init_directory_screen(self):
        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background-color: #F8FAFC;
                font-family: 'Segoe UI';
                color: #334155;
            }

            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #475569;
            }

            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #0F172A;
            }
        """)

        layout = QHBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        left_card = QFrame()
        left_card.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
        """)

        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(8)

        header_layout = QHBoxLayout()

        title = QLabel("Clinic Stock Directory")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #4F46E5;
            border: none;
        """)

        back_btn = QPushButton("Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px;
                font-size: 13px;
                background-color: #F1F5F9;
                border-radius: 6px;
                font-weight: bold;
                color: #475569;
                border: 1px solid #E2E8F0;
            }

            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """)

        back_btn.clicked.connect(self.clear_page)

        if self.on_back_to_menu is not None:
            back_btn.clicked.connect(self.on_back_to_menu)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)

        left_layout.addLayout(header_layout)

        search_filter_layout = QHBoxLayout()

        search_filter_layout.addWidget(QLabel("Search Criteria:"))

        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems([
            "Medicine Name",
            "Category / Use",
            "Barcode",
            "Active Ingredient"
        ])
        self.search_type_combo.setStyleSheet("""
            min-width: 150px;
            padding: 4px;
            font-size: 14px;
        """)
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)

        search_filter_layout.addWidget(self.search_type_combo)
        search_filter_layout.addStretch()

        left_layout.addLayout(search_filter_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Scan barcode or type a keyword to search stock directory..."
        )
        self.search_input.setStyleSheet("""
            padding: 10px;
            font-size: 14px;
        """)
        self.search_input.textChanged.connect(self.run_live_filter)

        left_layout.addWidget(self.search_input)

        self.master_table = QTableWidget()
        self.master_table.setColumnCount(4)
        self.master_table.setHorizontalHeaderLabels([
            "Medicine Name",
            "Category / Use",
            "Strength",
            "Total Available Qty"
        ])

        self.master_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.master_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.master_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.master_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.master_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        self.master_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background: #F8FAFC;
                font-size: 14px;
            }

            QHeaderView::section {
                background-color: #F1F5F9;
                font-weight: bold;
                color: #475569;
                border: none;
                padding: 8px;
                font-size: 14px;
            }

            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 30px;
                border-radius: 6px;
            }
        """)

        master_header = self.master_table.horizontalHeader()
        master_header.setSectionResizeMode(0, QHeaderView.Stretch)
        master_header.setSectionResizeMode(1, QHeaderView.Stretch)
        master_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        master_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.master_table.verticalHeader().setDefaultSectionSize(36)
        self.master_table.itemClicked.connect(self.handle_master_row_selection)

        left_layout.addWidget(self.master_table)
        layout.addWidget(left_card)

        self.internal_stack.addWidget(page)

    # =====================================================================
    # SCREEN 1: Batch details screen
    # =====================================================================
    def init_details_screen(self):
        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background-color: #F8FAFC;
                font-family: 'Segoe UI';
                color: #334155;
            }

            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #475569;
            }
        """)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        detail_card = QFrame()
        detail_card.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
        """)

        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(15, 15, 15, 15)
        detail_layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self.detail_title = QLabel("Medicine Batches Breakdown")
        self.detail_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #4F46E5;
            border: none;
        """)

        back_to_dir_btn = QPushButton("Back to Directory")
        back_to_dir_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_to_dir_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                background-color: #4F46E5;
                border-radius: 6px;
                font-weight: bold;
                color: white;
                border: none;
            }

            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        back_to_dir_btn.clicked.connect(
            lambda: self.internal_stack.setCurrentIndex(0)
        )

        header_layout.addWidget(self.detail_title)
        header_layout.addStretch()
        header_layout.addWidget(back_to_dir_btn)

        detail_layout.addLayout(header_layout)

        self.detail_desc = QLabel("")
        self.detail_desc.setStyleSheet("""
            font-size: 14px;
            color: #64748B;
            margin-bottom: 4px;
        """)
        detail_layout.addWidget(self.detail_desc)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(3)
        self.detail_table.setHorizontalHeaderLabels([
            "Batch Code",
            "Expiry Date",
            "Current Pills Count"
        ])
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.detail_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.detail_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detail_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        self.detail_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background: #F8FAFC;
                font-size: 14px;
            }

            QHeaderView::section {
                background-color: #F1F5F9;
                font-weight: bold;
                color: #475569;
                border: none;
                padding: 8px;
                font-size: 14px;
            }

            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 30px;
                border-radius: 6px;
            }
        """)

        self.detail_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.detail_table.verticalHeader().setDefaultSectionSize(36)

        detail_layout.addWidget(self.detail_table)
        layout.addWidget(detail_card)

        self.internal_stack.addWidget(page)

    # =====================================================================
    # Data refresh and display
    # =====================================================================
    def refresh_inventory_data(self):
        """
        Reload the inventory from the database and rebuild the visible table.
        """
        self.master_table.setRowCount(0)
        self.all_cached_inventory = []

        try:
            if (
                not hasattr(airtable_api, "stock_table")
                or airtable_api.stock_table is None
            ):
                return

            records = airtable_api.stock_table.all()

            for record in records:
                fields = (
                    record.fields
                    if hasattr(record, "fields")
                    else record.get("fields", {})
                )

                qty_raw = (
                    fields.get("Current Pills Count")
                    or fields.get("Quantity")
                    or fields.get("Pills Count")
                    or 0
                )

                try:
                    qty = int(float(qty_raw))
                except (ValueError, TypeError):
                    qty = 0

                if not fields.get("Medicine Name"):
                    continue

                # Hide empty stock rows completely from the inventory tables.
                if qty <= 0:
                    continue

                raw_barcode = (
                    fields.get("Barcode lookup")
                    or fields.get("Barcode")
                    or "NO_BARCODE"
                )

                if isinstance(raw_barcode, list):
                    clean_barcode = (
                        str(raw_barcode[0]).strip()
                        if raw_barcode
                        else "NO_BARCODE"
                    )
                else:
                    clean_barcode = str(raw_barcode).strip()

                category_value = (
                    fields.get("Category")
                    or fields.get("Category / Use")
                    or "General Medicine"
                )

                if isinstance(category_value, list):
                    category_value = (
                        category_value[0]
                        if category_value
                        else "General Medicine"
                    )

                self.all_cached_inventory.append({
                    "name": fields.get("Medicine Name", "Unknown"),
                    "barcode": clean_barcode,
                    "category": category_value,
                    "ingredient": fields.get("Active Ingredient", ""),
                    "dosage": fields.get("Dosage", "N/A"),
                    "qty": qty,
                    "batch": (
                        fields.get("A Batch")
                        or fields.get("Batch Number")
                        or "N/A"
                    ),
                    "expiry": fields.get("Expiry Date", "9999-12-31")
                })

            self.all_cached_inventory.sort(
                key=lambda item: item["expiry"]
            )

            self.show_items_in_grid(self.all_cached_inventory)

        except Exception as error:
            print(f"Error executing inventory matrix refresh: {error}")

    def show_items_in_grid(self, items_list):
        """
        Group all medicine batches by medicine name and show total quantity.
        """
        self.master_table.setRowCount(0)

        grouped_inventory = {}

        for item in items_list:
            key = item["name"].lower()

            if key not in grouped_inventory:
                grouped_inventory[key] = {
                    "name": item["name"],
                    "category": item["category"],
                    "dosage": item["dosage"],
                    "total_qty": 0,
                    "batches": []
                }

            grouped_inventory[key]["total_qty"] += item["qty"]
            grouped_inventory[key]["batches"].append(item)

        for row_index, data in enumerate(grouped_inventory.values()):
            self.master_table.insertRow(row_index)

            name_item = QTableWidgetItem(data["name"])
            category_item = QTableWidgetItem(str(data["category"]))
            dosage_item = QTableWidgetItem(str(data["dosage"]))
            qty_item = QTableWidgetItem(str(data["total_qty"]))

            name_item.setData(Qt.UserRole, data["batches"])

            self.master_table.setItem(row_index, 0, name_item)
            self.master_table.setItem(row_index, 1, category_item)
            self.master_table.setItem(row_index, 2, dosage_item)
            self.master_table.setItem(row_index, 3, qty_item)

    def handle_master_row_selection(self, item):
        """
        Open the details screen for the selected medicine.
        """
        row = item.row()
        name_cell = self.master_table.item(row, 0)

        if name_cell is None:
            return

        batches = name_cell.data(Qt.UserRole)

        if not batches:
            return

        self.detail_title.setText(
            f"Batches Breakdown: {batches[0]['name']}"
        )
        self.detail_desc.setText(
            "Detailed overview of the batches currently in storage."
        )

        self.detail_table.setRowCount(0)

        for row_index, batch in enumerate(batches):
            self.detail_table.insertRow(row_index)

            self.detail_table.setItem(
                row_index,
                0,
                QTableWidgetItem(str(batch["batch"]))
            )
            self.detail_table.setItem(
                row_index,
                1,
                QTableWidgetItem(str(batch["expiry"]))
            )
            self.detail_table.setItem(
                row_index,
                2,
                QTableWidgetItem(str(batch["qty"]))
            )

        self.internal_stack.setCurrentIndex(1)

    def run_live_filter(self):
        """
        Filter the inventory using the selected search method.
        """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()

        if not search_text:
            self.show_items_in_grid(self.all_cached_inventory)
            return

        filtered = []

        for medicine in self.all_cached_inventory:
            value_to_check = ""

            if search_type == "Medicine Name":
                value_to_check = medicine["name"]
            elif search_type == "Category / Use":
                value_to_check = medicine["category"]
            elif search_type == "Barcode":
                value_to_check = medicine["barcode"]
            elif search_type == "Active Ingredient":
                value_to_check = medicine["ingredient"]

            if search_text in str(value_to_check).lower():
                filtered.append(medicine)

        self.show_items_in_grid(filtered)

    # =====================================================================
    # Important fix:
    # Refresh every time this page becomes visible.
    # =====================================================================
    def showEvent(self, event):
        """
        Refresh the inventory whenever the user enters this screen.
        """
        self.internal_stack.setCurrentIndex(0)
        self.search_input.clear()
        self.detail_table.setRowCount(0)

        self.refresh_inventory_data()

        super().showEvent(event)

    def clear_page(self):
        """
        Clear the visible state before returning to the menu.
        The database refresh is now done when the page is opened.
        """
        self.search_input.clear()
        self.master_table.setRowCount(0)
        self.detail_table.setRowCount(0)
        self.internal_stack.setCurrentIndex(0)
