import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QStackedWidget
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


class InventoryViewPage(QWidget):
    """
    Modern Clinic Inventory Browser using a clean multi-screen Stacked UI.
    Optimized with custom Scrollbars and large readable fonts for clear visibility.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.current_focused_input = None
        self.all_cached_inventory = []

        # Internal stack configuration to separate overview and detail screens
        self.internal_stack = QStackedWidget(self)

        self.init_directory_screen()  # Index 0
        self.init_details_screen()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

        # 🔥 Trigger immediate database data sync upon workspace initialization
        self.refresh_inventory_data()

    # =====================================================================
    # 🎴 SCREEN 0: Full Width Main Directory Screen (With Scroll & Large Text)
    # =====================================================================
    def init_directory_screen(self):
        page = QWidget()
        page.setStyleSheet("""
            QWidget { background-color: #F8FAFC; font-family: 'Segoe UI'; color: #334155; }
            QLabel { font-size: 14px; font-weight: 600; color: #475569; }
            QLineEdit, QComboBox { 
                padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; 
                font-size: 14px; background-color: #FFFFFF; color: #0F172A;
            }
        """)

        layout = QHBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        title = QLabel("📋 Clinic Stock Directory")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4F46E5; border: none;")

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; font-size: 13px; background-color: #F1F5F9; border-radius: 6px; 
                font-weight: bold; color: #475569; border: 1px solid #E2E8F0;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.clear_page)
        back_btn.clicked.connect(self.on_back_to_menu)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        search_filter_layout = QHBoxLayout()
        search_filter_layout.addWidget(QLabel("Search Criteria:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Medicine Name", "Category / Use", "Barcode", "Active Ingredient"])
        self.search_type_combo.setStyleSheet("min-width: 150px; padding: 4px; font-size: 14px;")
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)
        search_filter_layout.addWidget(self.search_type_combo)
        search_filter_layout.addStretch()
        left_layout.addLayout(search_filter_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or type a keyword to search stock directory...")
        self.search_input.setStyleSheet("padding: 10px; font-size: 14px;")
        self.search_input.textChanged.connect(self.run_live_filter)

        self.search_input.focusInEvent = lambda event: self.handle_input_focus(self.search_input, event)
        self.search_input.installEventFilter(self)
        left_layout.addWidget(self.search_input)

        # Full width master layout configuration with Scrollbars activated
        self.master_table = QTableWidget()
        self.master_table.setColumnCount(4)
        self.master_table.setHorizontalHeaderLabels(
            ["Medicine Name", "Category / Use", "Strength", "Total Available Qty"])
        self.master_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.master_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.master_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.master_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.master_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        self.master_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; background: #F8FAFC; font-size: 14px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; color: #475569; border: none; padding: 8px; font-size: 14px; }
            QScrollBar:vertical {
                border: none; background: #F1F5F9; width: 12px; margin: 0px; border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1; min-height: 30px; border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)

        master_header = self.master_table.horizontalHeader()
        master_header.setSectionResizeMode(0, QHeaderView.Stretch)
        master_header.setSectionResizeMode(1, QHeaderView.Stretch)
        master_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        master_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.master_table.verticalHeader().setDefaultSectionSize(36)

        self.master_table.itemClicked.connect(self.handle_master_row_selection)
        left_layout.addWidget(self.master_table)
        layout.addWidget(left_card, stretch=6)

        # ⌨️ Integrated Virtual Keyboard Section
        self.kb_card = QFrame()
        self.kb_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(self.kb_card)
        kb_layout.setContentsMargins(8, 8, 8, 8)
        kb_layout.setSpacing(4)

        title_kb = QLabel("⌨️ Touch Keyboard Workspace")
        title_kb.setStyleSheet("font-size: 12px; color: #64748B; font-weight: bold; border: none; margin-bottom: 2px;")
        kb_layout.addWidget(title_kb)

        keyboard_widget = QWidget()
        keyboard_lay = QVBoxLayout(keyboard_widget)
        keyboard_lay.setContentsMargins(0, 0, 0, 0)
        keyboard_lay.setSpacing(4)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            [' ', 'Clear', '⌫', '🔽 Hide']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(42)

                if key in ['Clear', '⌫', '🔽 Hide']:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #CBD5E1; color: #1E293B; font-weight: bold; font-size: 12px; border-radius: 5px; border: none; }
                        QPushButton:pressed { background-color: #94A3B8; }
                    """)
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 5px; min-width: 55px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 5px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            keyboard_lay.addLayout(r_lay)

        kb_layout.addLayout(keyboard_lay)
        kb_layout.addStretch()
        layout.addWidget(self.kb_card, stretch=4)

        self.kb_card.hide()
        self.internal_stack.addWidget(page)

    # =====================================================================
    # 🎴 SCREEN 1: Full Width Detailed Batches Breakdown Screen
    # =====================================================================
    def init_details_screen(self):
        page = QWidget()
        page.setStyleSheet("""
            QWidget { background-color: #F8FAFC; font-family: 'Segoe UI'; color: #334155; }
            QLabel { font-size: 14px; font-weight: 600; color: #475569; }
        """)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        detail_card = QFrame()
        detail_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(15, 15, 15, 15)
        detail_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        self.detail_title = QLabel("Medicine Batches Breakdown")
        self.detail_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4F46E5; border: none;")

        back_to_dir_btn = QPushButton("⬅️ Back to Directory")
        back_to_dir_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_to_dir_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px; font-size: 13px; background-color: #4F46E5; border-radius: 6px; 
                font-weight: bold; color: white; border: none;
            }
            QPushButton:hover { background-color: #4338CA; }
        """)
        back_to_dir_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))

        header_layout.addWidget(self.detail_title)
        header_layout.addStretch()
        header_layout.addWidget(back_to_dir_btn)
        detail_layout.addLayout(header_layout)

        self.detail_desc = QLabel("")
        self.detail_desc.setStyleSheet("font-size: 14px; color: #64748B; margin-bottom: 4px;")
        detail_layout.addWidget(self.detail_desc)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(3)
        self.detail_table.setHorizontalHeaderLabels(["Batch Code", "Expiry Date", "Current Pills Count"])
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.detail_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.detail_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detail_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        self.detail_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; background: #F8FAFC; font-size: 14px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; color: #475569; border: none; padding: 8px; font-size: 14px; }
            QScrollBar:vertical {
                border: none; background: #F1F5F9; width: 12px; margin: 0px; border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1; min-height: 30px; border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detail_table.verticalHeader().setDefaultSectionSize(36)
        detail_layout.addWidget(self.detail_table)

        layout.addWidget(detail_card)
        self.internal_stack.addWidget(page)

    # =====================================================================
    # ⚙️ INTERACTIVE LAYOUT HANDLING LOGIC & MUTATIONS
    # =====================================================================
    def refresh_inventory_data(self):
        """ Downloads latest stock records maps while normalizing lookups cleanly """
        self.master_table.setRowCount(0)
        self.all_cached_inventory = []

        try:
            if not hasattr(airtable_api, 'stock_table') or airtable_api.stock_table is None: return
            records = airtable_api.stock_table.all()

            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})

                # 🔥 إصلاح مرن وقوي: جلب القيمة الرقمية للكمية بفحص الأسماء المحتملة في السيرفر لضمان قراءة الجدول كاملاً
                qty_raw = fields.get("Current Pills Count") or fields.get("Quantity") or fields.get("Pills Count") or 0

                # إذا كانت كمية الدواء فارغة أو نصية من صيغ الإدخال الأخرى
                try:
                    qty = int(float(qty_raw))
                except (ValueError, TypeError):
                    qty = 0

                # نعرض الدواء طالما الاسم موجود، حتى لو كانت الكمية صفرية في بعض الدفعات التاريخية لضمان اكتمال السجلات
                if fields.get("Medicine Name"):
                    raw_b = fields.get("Barcode lookup") or fields.get("Barcode", "NO_BARCODE")
                    if isinstance(raw_b, list):
                        clean_b = str(raw_b[0]).strip() if raw_b else "NO_BARCODE"
                    else:
                        clean_b = str(raw_b).strip()

                    # استخراج فئة الاستخدام بدقة ومطابقتها مع الحقل الظاهر في السيرفر
                    category_val = fields.get("Category") or fields.get("Category / Use") or "General Medicine"
                    if isinstance(category_val, list): category_val = category_val[0]

                    self.all_cached_inventory.append({
                        "name": fields.get("Medicine Name", "Unknown"),
                        "barcode": clean_b,
                        "category": category_val,
                        "ingredient": fields.get("Active Ingredient", ""),
                        "dosage": fields.get("Dosage", "N/A"),
                        "qty": qty,
                        "batch": fields.get("A Batch") or fields.get("Batch Number") or "N/A",
                        "expiry": fields.get("Expiry Date", "9999-12-31")
                    })

            self.all_cached_inventory.sort(key=lambda x: x['expiry'])

            # 🔥 جلب وعرض البيانات فوراً بالوضع الافتراضي عند فتح الصفحة
            self.show_items_in_grid(self.all_cached_inventory)
        except Exception as e:
            print(f"Error executing inventory matrix refresh: {e}")

    def show_items_in_grid(self, items_list):
        """ Groups inventory rows smoothly into full width table headers """
        self.master_table.setRowCount(0)

        grouped_inventory = {}
        for item in items_list:
            # نجمع الأدوية المتطابقة بالاسم أو الباركود لمنع التكرار بصرياً في الواجهة الرئيسية
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

        for idx, (k, data) in enumerate(grouped_inventory.items()):
            self.master_table.insertRow(idx)

            name_item = QTableWidgetItem(data["name"])
            category_item = QTableWidgetItem(data["category"])
            dosage_item = QTableWidgetItem(str(data["dosage"]))
            qty_item = QTableWidgetItem(str(data["total_qty"]))

            name_item.setData(Qt.UserRole, data["batches"])

            self.master_table.setItem(idx, 0, name_item)
            self.master_table.setItem(idx, 1, category_item)
            self.master_table.setItem(idx, 2, dosage_item)
            self.master_table.setItem(idx, 3, qty_item)

    def handle_master_row_selection(self, item):
        """ Routes selection tracking to full width breakdown dashboard index """
        row = item.row()
        name_cell = self.master_table.item(row, 0)
        batches = name_cell.data(Qt.UserRole)

        if not batches: return

        self.kb_card.hide()

        self.detail_title.setText(f"📋 Batches Breakdown: {batches[0]['name']}")
        self.detail_desc.setText(
            f"Detailed overview of separate batches currently in storage for this medicine selection.")
        self.detail_table.setRowCount(0)

        for idx, b in enumerate(batches):
            self.detail_table.insertRow(idx)
            self.detail_table.setItem(idx, 0, QTableWidgetItem(str(b["batch"])))
            self.detail_table.setItem(idx, 1, QTableWidgetItem(str(b["expiry"])))
            self.detail_table.setItem(idx, 2, QTableWidgetItem(str(b["qty"])))

        self.internal_stack.setCurrentIndex(1)

    def handle_input_focus(self, input_field, event):
        self.current_focused_input = input_field
        if event: super(QLineEdit, input_field).focusInEvent(event)
        input_field.setStyleSheet(
            "padding: 10px; border: 2px solid #6366F1; border-radius: 6px; font-size: 14px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")
        input_field.setFocus(Qt.OtherFocusReason)

    def eventFilter(self, obj, event):
        if obj == self.search_input and event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
            self.kb_card.show()
            self.search_input.setStyleSheet(
                "padding: 10px; border: 2px solid #6366F1; border-radius: 6px; font-size: 14px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()

        if key == '🔽 Hide':
            self.kb_card.hide()
            self.search_input.setStyleSheet(
                "padding: 10px; font-size: 14px; background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px;")
            return
        elif key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)
        self.current_focused_input.setFocus(Qt.OtherFocusReason)

    def run_live_filter(self):
        """ Filters master stock fields tracking variables cleanly """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()

        # إذا تم مسح مربع البحث، يعود لعرض القائمة كاملة فوراً
        if not search_text:
            self.show_items_in_grid(self.all_cached_inventory)
            return

        filtered = []
        for med in self.all_cached_inventory:
            val_to_check = ""
            if search_type == "Medicine Name":
                val_to_check = med["name"]
            elif search_type == "Category / Use":
                val_to_check = med["category"]
            elif search_type == "Barcode":
                val_to_check = med["barcode"]
            elif search_type == "Active Ingredient":
                val_to_check = med["ingredient"]

            if search_text in str(val_to_check).lower():
                filtered.append(med)

        self.show_items_in_grid(filtered)

    def clear_page(self):
        self.search_input.clear()
        self.master_table.setRowCount(0)
        self.detail_table.setRowCount(0)
        self.refresh_inventory_data()
        self.kb_card.hide()
        self.search_input.setStyleSheet(
            "padding: 10px; font-size: 14px; background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.internal_stack.setCurrentIndex(0)