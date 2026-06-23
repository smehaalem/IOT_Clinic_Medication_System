import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QListWidget, QListWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


class InventoryViewPage(QWidget):
    """
    Modern Inventory Browser with dynamic live filtering and touch keyboard.
    ⚠️ UPDATED: Supports Airtable Barcode Lookup fields and optimized Touch Layout.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.current_focused_input = None
        self.all_cached_inventory = []

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #F8FAFC; font-family: 'Segoe UI'; color: #334155; }
            QLabel { font-size: 12px; font-weight: 500; color: #475569; }
            QLineEdit, QComboBox { 
                padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; 
                font-size: 11px; background-color: #FFFFFF; color: #0F172A;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        title = QLabel("📋 View Clinic Inventory")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4F46E5; border: none;")

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 10px; font-size: 11px; background-color: #F1F5F9; border-radius: 6px; 
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
        search_filter_layout.addWidget(QLabel("Search:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Barcode", "Medicine Name", "Active Ingredient", "Batch ID"])
        self.search_type_combo.setStyleSheet("min-width: 120px; padding: 4px; font-size: 11px;")
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)
        search_filter_layout.addWidget(self.search_type_combo)
        search_filter_layout.addStretch()
        left_layout.addLayout(search_filter_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or type to filter...")
        self.search_input.setStyleSheet("padding: 8px; font-size: 12px;")
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.returnPressed.connect(self.run_live_filter)

        self.search_input.focusInEvent = lambda event: self.handle_input_focus(self.search_input, event)
        self.search_input.installEventFilter(self)
        left_layout.addWidget(self.search_input)

        self.inventory_list_widget = QListWidget()
        self.inventory_list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 11px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #F1F5F9; color: #1E293B; }
        """)
        left_layout.addWidget(self.inventory_list_widget)

        main_layout.addWidget(left_card, stretch=5)

        # ⌨️ كيبورد اللمس المطور والمحمي من السحق عمودياً لشاشات الرازبري
        self.kb_card = QFrame()
        self.kb_card.setStyleSheet("background-color: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(self.kb_card)
        kb_layout.setContentsMargins(8, 8, 8, 8)
        kb_layout.setSpacing(4)

        title_kb = QLabel("⌨️ Touch Workspace Keyboard")
        title_kb.setStyleSheet("font-size: 11px; color: #64748B; font-weight: bold; border: none; margin-bottom: 2px;")
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

                # 🔥 تمديد الارتفاع عمودياً لراحة إصبع الطبيب أو الممرض ومنع حشر الأزرار
                btn.setMinimumHeight(42)

                if key in ['Clear', '⌫', '🔽 Hide']:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #CBD5E1; color: #1E293B; font-weight: bold; font-size: 11px; border-radius: 5px; border: none; padding: 6px 0px; }
                        QPushButton:pressed { background-color: #94A3B8; }
                    """)
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 11px; border: 1px solid #CBD5E1; border-radius: 5px; min-width: 55px; padding: 6px 0px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 11px; border: 1px solid #CBD5E1; border-radius: 5px; padding: 6px 0px; }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            keyboard_lay.addLayout(r_lay)

        kb_layout.addLayout(keyboard_lay)
        kb_layout.addStretch()

        main_layout.addWidget(self.kb_card, stretch=5)

        self.kb_card.hide()

        self.current_focused_input = self.search_input
        self.search_input.setFocus()

    def refresh_inventory_data(self):
        """ جلب البيانات وترتيبها تلقائياً مع تفكيك حقل الباركود اللوك أب الجديد """
        self.inventory_list_widget.clear()
        self.all_cached_inventory = []
        try:
            if not hasattr(airtable_api, 'stock_table') or airtable_api.stock_table is None: return
            records = airtable_api.stock_table.all()

            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                qty = int(fields.get("Current Pills Count", 0))
                if qty > 0:
                    # 🔥 معالجة جلب الباركود النظيف من حقل الـ Lookup الجديد كلياً لمنع المشاكل
                    raw_b = fields.get("Barcode lookup") or fields.get("Barcode", "")
                    if isinstance(raw_b, list):
                        clean_b = str(raw_b[0]).strip() if raw_b else ""
                    else:
                        clean_b = str(raw_b).strip()

                    self.all_cached_inventory.append({
                        "name": fields.get("Medicine Name", "Unknown"),
                        "barcode": clean_b,
                        "ingredient": fields.get("Active Ingredient", ""),
                        "dosage": fields.get("Dosage", ""),
                        "qty": qty,
                        "batch": fields.get("A Batch", "N/A"),
                        "expiry": fields.get("Expiry Date", "9999-12-31")
                    })

            # ترتيب البيانات من الأقرب صلاحية إلى الأبعد
            self.all_cached_inventory.sort(key=lambda x: x['expiry'])

            self.show_items_in_list(self.all_cached_inventory)
        except Exception as e:
            print(f"Error loading inventory screen: {e}")

    def show_items_in_list(self, items_list):
        self.inventory_list_widget.clear()
        for med in items_list:
            # هنا الباركود جاهز ومنظف كنص صريح مباشر
            display_text = f"📅 [{med['expiry']}] | 💊 {med['name']} ({med['dosage']}) | Code: {med['barcode']} | Batch: {med['batch']} | Qty: {med['qty']}"
            self.inventory_list_widget.addItem(QListWidgetItem(display_text))

    def handle_input_focus(self, input_field, event):
        self.current_focused_input = input_field
        if event:
            super(QLineEdit, input_field).focusInEvent(event)
        input_field.setStyleSheet(
            "padding: 8px; border: 2px solid #6366F1; border-radius: 6px; font-size: 12px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")
        input_field.setFocus(Qt.OtherFocusReason)

    def eventFilter(self, obj, event):
        s_input = getattr(self, 'search_input', None)
        if obj == s_input and s_input is not None:
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
                self.kb_card.show()
                s_input.setStyleSheet(
                    "padding: 8px; border: 2px solid #6366F1; border-radius: 6px; font-size: 12px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()

        if key == '🔽 Hide':
            self.kb_card.hide()
            self.search_input.setStyleSheet(
                "padding: 8px; font-size: 12px; background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px;")
            return
        elif key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)

        self.current_focused_input.setFocus(Qt.OtherFocusReason)

    def run_live_filter(self):
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()

        if not search_text:
            self.show_items_in_list(self.all_cached_inventory)
            return

        filtered = []
        for med in self.all_cached_inventory:
            field_val = ""
            if search_type == "Medicine Name":
                val_to_check = med["name"]
            elif search_type == "Barcode":
                val_to_check = med["barcode"]
            elif search_type == "Active Ingredient":
                val_to_check = med["ingredient"]
            elif search_type == "Batch ID":
                val_to_check = med["batch"]

            val_to_check = str(val_to_check).lower()
            if search_text in val_to_check:
                filtered.append(med)

        self.show_items_in_list(filtered)

    def clear_page(self):
        self.search_input.clear()
        self.inventory_list_widget.clear()
        self.all_cached_inventory = []
        self.kb_card.hide()
        self.search_input.setStyleSheet(
            "padding: 8px; font-size: 12px; background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px;")