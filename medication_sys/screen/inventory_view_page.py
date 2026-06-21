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
    ⚠️ UPDATED: Automatically sorts medication by Expiry Date (Soonest first).
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
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A; border: none;")

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "padding: 4px 10px; font-size: 11px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; color: #475569; border: 1px solid #E2E8F0;")
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
        self.inventory_list_widget.setStyleSheet(
            "border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 11px;")
        left_layout.addWidget(self.inventory_list_widget)

        main_layout.addWidget(left_card, stretch=5)

        self.kb_card = QFrame()
        self.kb_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(self.kb_card)

        keyboard_widget = QWidget()
        keyboard_lay = QVBoxLayout(keyboard_widget)
        keyboard_lay.setContentsMargins(0, 0, 0, 0)
        keyboard_lay.setSpacing(3)
        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            [' ', 'Clear', '⌫', '🔽 Hide']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(3)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(
                    "background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 10px 2px; font-size: 11px; border-radius: 4px; border: 1px solid #E2E8F0;")
                if key in ['Clear', '⌫', '🔽 Hide']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 10px 2px; font-size: 11px; border-radius: 4px; border: none;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 10px 2px; font-size: 11px; border-radius: 4px; min-width: 50px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            keyboard_lay.addLayout(r_lay)
        kb_layout.addWidget(keyboard_widget)
        kb_layout.addStretch()

        main_layout.addWidget(self.kb_card, stretch=4)

        self.kb_card.hide()

        self.current_focused_input = self.search_input
        self.search_input.setFocus()

    def refresh_inventory_data(self):
        """ جلب البيانات وترتيبها تلقائياً من التاريخ الأقرب للانتهاء إلى الأبعد """
        self.inventory_list_widget.clear()
        self.all_cached_inventory = []
        try:
            if not hasattr(airtable_api, 'stock_table') or airtable_api.stock_table is None: return
            records = airtable_api.stock_table.all()

            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                qty = int(fields.get("Current Pills Count", 0))
                if qty > 0:
                    self.all_cached_inventory.append({
                        "name": fields.get("Medicine Name", "Unknown"),
                        "barcode": fields.get("Barcode", ""),
                        "ingredient": fields.get("Active Ingredient", ""),
                        "dosage": fields.get("Dosage", ""),
                        "qty": qty,
                        "batch": fields.get("A Batch", "N/A"),
                        "expiry": fields.get("Expiry Date", "9999-12-31")  # وضع تاريخ افتراضي بعيد في حال خلو الحقل
                    })

            # 🔥 الذكاء المطلوب: ترتيب الداتا لايف بناءً على الـ Expiry Date (الأقرب فالأبعد)
            self.all_cached_inventory.sort(key=lambda x: x['expiry'])

            self.show_items_in_list(self.all_cached_inventory)
        except Exception as e:
            print(f"Error loading inventory screen: {e}")

    def show_items_in_list(self, items_list):
        self.inventory_list_widget.clear()
        for med in items_list:
            clean_b = med['barcode'][0] if isinstance(med['barcode'], list) else med['barcode']
            # إضافة تاريخ انتهاء الصلاحية بشكل بارز بجانب كل دواء في القائمة
            display_text = f"📅 [{med['expiry']}] | 💊 {med['name']} ({med['dosage']}) | Code: {clean_b} | Batch: {med['batch']} | Qty: {med['qty']}"
            self.inventory_list_widget.addItem(QListWidgetItem(display_text))

    def handle_input_focus(self, input_field, event):
        self.current_focused_input = input_field
        super(QLineEdit, input_field).focusInEvent(event)
        input_field.setFocus(Qt.OtherFocusReason)

    def eventFilter(self, obj, event):
        s_input = getattr(self, 'search_input', None)
        if obj == s_input and s_input is not None:
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
                self.kb_card.show()
                s_input.setStyleSheet(
                    "padding: 8px; border: 2px solid #0D9488; border-radius: 6px; font-size: 12px; background-color: #F0FDFA; color: #0F172A; font-weight: bold;")
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()

        if key == '🔽 Hide':
            self.kb_card.hide()
            self.search_input.setStyleSheet("padding: 8px; font-size: 12px; background-color: #FFFFFF; color: #0F172A;")
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
                field_val = med["name"]
            elif search_type == "Barcode":
                field_val = med["barcode"]
            elif search_type == "Active Ingredient":
                field_val = med["ingredient"]
            elif search_type == "Batch ID":
                field_val = med["batch"]

            if isinstance(field_val, list):
                field_val = field_val[0] if field_val else ""

            field_val = str(field_val).lower()

            if search_text in field_val:
                filtered.append(med)

        self.show_items_in_list(filtered)

    def clear_page(self):
        self.search_input.clear()
        self.inventory_list_widget.clear()
        self.all_cached_inventory = []
        self.kb_card.hide()
        self.search_input.setStyleSheet("padding: 8px; font-size: 12px; background-color: #FFFFFF; color: #0F172A;")