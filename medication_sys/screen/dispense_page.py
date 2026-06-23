import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QListWidget, QListWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


class DispenseMedicationPage(QWidget):
    """
    Smart Medication Dispensing Screen.
    ⚠️ UPDATED: Fully supports Airtable Barcode Lookup fields (Handles Linked Lists).
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.user_role = "User"
        self.user_full_name = "System User"
        self.current_focused_input = None
        self.scanned_barcode = ""
        self.loaded_batches = []
        self.all_cached_inventory = []

        self.internal_stack = QStackedWidget(self)

        self.init_scan_screen()  # Index 0
        self.init_selection_screen()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

    def set_user_session(self, role, full_name):
        self.user_role = str(role).strip().lower()
        self.user_full_name = str(full_name).strip()
        self.preload_inventory_cache()

    def preload_inventory_cache(self):
        self.all_cached_inventory = []
        try:
            if not hasattr(airtable_api, 'stock_table') or airtable_api.stock_table is None:
                return
            records = airtable_api.stock_table.all()
            if not records: return

            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                qty = int(fields.get("Current Pills Count", 0))
                if qty > 0:
                    # 🔥 استخراج الباركود الذكي من حقل الـ Lookup أو الحقل العادي
                    raw_b = fields.get("Barcode lookup") or fields.get("Barcode", "")
                    if isinstance(raw_b, list):
                        clean_b = str(raw_b[0]).strip() if raw_b else ""
                    else:
                        clean_b = str(raw_b).strip()

                    self.all_cached_inventory.append({
                        "id": r.id if hasattr(r, 'id') else r.get('id'),
                        "name": fields.get("Medicine Name", ""),
                        "barcode": clean_b,  # حفظ الباركود الصافي كنص وليس كـ List
                        "ingredient": fields.get("Active Ingredient", ""),
                        "dosage": fields.get("Dosage", ""),
                        "qty": qty,
                        "batch": fields.get("A Batch", "N/A"),
                        "expiry": fields.get("Expiry Date", "")
                    })
        except Exception as e:
            print(f"⚠️ Stock cache bypassed or empty: {e}")

    # =====================================================================
    # 🎴 SCREEN 0: Live Search & Scanner Entry
    # =====================================================================
    def init_scan_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        title = QLabel("📦 Dispense Medicine")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4F46E5; border: none;")

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; font-size: 12px; background-color: #F1F5F9; border-radius: 6px; 
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

        search_type_layout = QHBoxLayout()
        lbl = QLabel("Filter By:")
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        search_type_layout.addWidget(lbl)

        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Barcode", "Medicine Name", "Active Ingredient", "Batch ID"])
        self.search_type_combo.setStyleSheet("""
            QComboBox { padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px; background-color: #FFFFFF; color: #1E293B; min-width: 140px; }
        """)
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)
        search_type_layout.addWidget(self.search_type_combo)
        search_type_layout.addStretch()
        left_layout.addLayout(search_type_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or type to search...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px;")
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.returnPressed.connect(self.handle_scanner_return_pressed)

        self.search_input.focusInEvent = lambda event: self.handle_input_focus(self.search_input, event)
        self.search_input.installEventFilter(self)
        left_layout.addWidget(self.search_input)

        self.live_matches_list = QListWidget()
        self.live_matches_list.setStyleSheet("""
            QListWidget { border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 12px; padding: 4px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #F1F5F9; border-radius: 4px; }
            QListWidget::item:selected { background-color: #EEF2FF; color: #4F46E5; font-weight: bold; }
        """)
        self.live_matches_list.itemClicked.connect(self.handle_live_item_selection)
        left_layout.addWidget(self.live_matches_list)

        main_layout.addWidget(left_card, stretch=5)

        # ⌨️ لوحة المفاتيح اللمسية الموسعة
        self.kb_card = QFrame()
        self.kb_card.setStyleSheet("background-color: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(self.kb_card)
        kb_layout.setContentsMargins(10, 10, 10, 10)
        kb_layout.setSpacing(5)

        title_kb = QLabel("⌨️ Touch Workspace Keyboard")
        title_kb.setStyleSheet("font-size: 11px; color: #64748B; font-weight: bold; border: none; margin-bottom: 2px;")
        kb_layout.addWidget(title_kb)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            [' ', 'Clear', '⌫', '🔽']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(42)

                if key in ['Clear', '⌫', '🔽']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; font-size: 12px; border-radius: 6px; border: none;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 6px; min-width: 60px;")
                else:
                    btn.setStyleSheet(
                        "background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 6px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            kb_layout.addLayout(r_lay)
        kb_layout.addStretch()
        main_layout.addWidget(self.kb_card, stretch=5)

        self.kb_card.hide()
        self.internal_stack.addWidget(page)

    # =====================================================================
    # 🎴 SCREEN 1: Quantity Selection & Batch Info
    # =====================================================================
    def init_selection_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        form_card = QFrame()
        form_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(8)

        self.med_name_title = QLabel("Medicine: Loading...")
        self.med_name_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4F46E5;")
        form_layout.addWidget(self.med_name_title)

        self.total_stock_lbl = QLabel("Total Available: --")
        self.total_stock_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #2563EB;")
        form_layout.addWidget(self.total_stock_lbl)

        self.stock_list_widget = QListWidget()
        self.stock_list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 12px; padding: 4px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #F1F5F9; color: #334155; }
        """)
        form_layout.addWidget(self.stock_list_widget)

        form_layout.addWidget(
            QLabel("Deduction Quantity", styleSheet="font-size: 11px; font-weight: bold; color: #475569;"))
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter dosage/pills quantity count...")
        self.quantity_input.setStyleSheet(
            "padding: 8px; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 6px;")

        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event)
        self.quantity_input.installEventFilter(self)
        form_layout.addWidget(self.quantity_input)

        self.dispense_btn = QPushButton("⚡ Confirm & Dispense Now")
        self.dispense_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.dispense_btn.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.dispense_btn.clicked.connect(self.execute_smart_dispense)
        form_layout.addWidget(self.dispense_btn)

        nav_layout = QHBoxLayout()
        another_btn = QPushButton("🔄 Scan Another")
        another_btn.setCursor(QCursor(Qt.PointingHandCursor))
        another_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #475569; padding: 8px; font-size: 12px; font-weight: bold; border-radius: 6px; border: 1px solid #E2E8F0; }
        """)
        another_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))

        finish_btn = QPushButton("🏁 Finish")
        finish_btn.setCursor(QCursor(Qt.PointingHandCursor))
        finish_btn.setStyleSheet("""
            QPushButton { background-color: #4F46E5; color: white; padding: 8px; font-size: 12px; font-weight: bold; border-radius: 6px; border: none; }
        """)
        finish_btn.clicked.connect(self.clear_page)
        finish_btn.clicked.connect(self.on_back_to_menu)

        nav_layout.addWidget(another_btn, stretch=1)
        nav_layout.addWidget(finish_btn, stretch=1)
        form_layout.addLayout(nav_layout)

        main_layout.addWidget(form_card, stretch=5)

        # 🧮 لوحة الأرقام
        self.kb_card_s2 = QFrame()
        self.kb_card_s2.setStyleSheet("background-color: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_lay2 = QVBoxLayout(self.kb_card_s2)
        kb_lay2.setContentsMargins(10, 10, 10, 10)

        title_kb2 = QLabel("🧮 Numerical Pad")
        title_kb2.setStyleSheet("font-size: 11px; color: #64748B; font-weight: bold; border: none; margin-bottom: 4px;")
        kb_lay2.addWidget(title_kb2)

        num_grid2 = QVBoxLayout()
        num_grid2.setSpacing(4)
        rows2 = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['Clear', '0', '⌫', '🔽']]
        for r in rows2:
            rl = QHBoxLayout()
            rl.setSpacing(4)
            for key in r:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(45)

                if key in ['Clear', '⌫', '🔽']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; font-size: 12px; border-radius: 6px; border: none;")
                else:
                    btn.setStyleSheet(
                        "background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 13px; border: 1px solid #CBD5E1; border-radius: 6px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                rl.addWidget(btn)
            num_grid2.addLayout(rl)
        kb_lay2.addLayout(num_grid2)
        kb_lay2.addStretch()
        main_layout.addWidget(self.kb_card_s2, stretch=4)

        self.kb_card_s2.hide()
        self.internal_stack.addWidget(page)

    # =====================================================================
    # ⚙️ INTERACTIVE UX & LOOKUP PARSING LOGIC
    # =====================================================================
    def handle_input_focus(self, input_field, event):
        for box in [self.search_input, self.quantity_input]:
            box.setStyleSheet(
                "padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px; background-color: #F8FAFC; color: #1E293B;")
        self.current_focused_input = input_field
        if event: super(QLineEdit, input_field).focusInEvent(event)
        input_field.setStyleSheet(
            "padding: 8px; border: 2px solid #6366F1; border-radius: 6px; font-size: 12px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")

    def eventFilter(self, obj, event):
        if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
            if obj == self.search_input:
                self.kb_card.show()
            elif obj == self.quantity_input:
                self.kb_card_s2.show()
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()
        if key == '🔽':
            if self.internal_stack.currentIndex() == 0:
                self.kb_card.hide()
            else:
                self.kb_card_s2.hide()
            return
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)
        self.current_focused_input.setFocus(Qt.OtherFocusReason)

    def run_live_filter(self):
        """ فلترة المخزون حياً بناءً على فك اللستة لحقل الباركود الجديد """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()
        self.live_matches_list.clear()

        if not search_text or not self.all_cached_inventory: return

        matched_items = []
        for med in self.all_cached_inventory:
            val_to_check = ""
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
                matched_items.append(med)

        seen_barcodes = set()
        for med in matched_items:
            clean_b = med['barcode']  # هنا الباركود جاهز ونظيف كنص صريح
            if clean_b not in seen_barcodes:
                seen_barcodes.add(clean_b)
                display_text = f"💊 {med['name']} | Strength: {med['dosage']} | (Code: {clean_b})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, clean_b)
                self.live_matches_list.addItem(item)

    def handle_scanner_return_pressed(self):
        barcode = self.search_input.text().strip()
        if barcode:
            if self.live_matches_list.count() > 0:
                best_item = self.live_matches_list.item(0)
                barcode = best_item.data(Qt.UserRole)
            self.kb_card.hide()
            self.process_barcode_routing(explicit_barcode=barcode)

    def handle_live_item_selection(self, item):
        barcode = item.data(Qt.UserRole)
        if barcode:
            self.kb_card.hide()
            self.process_barcode_routing(explicit_barcode=barcode)

    def process_barcode_routing(self, explicit_barcode=None):
        """ جلب الداتا ومعالجة مطابقة حقل الباركود اللوك أب المفتوح """
        barcode = explicit_barcode or self.search_input.text().strip()
        if not barcode: return
        barcode = str(barcode).strip()

        self.scanned_barcode = barcode
        self.stock_list_widget.clear()

        try:
            self.loaded_batches = airtable_api.find_all_batches_by_barcode(barcode)

            # 🔥 Fallback حرج: مطابقة يدويّة داخل كاش الكلاس للتغلب على مشاكل نوع حقل الـ Linked Field بالسيرفر
            if not self.loaded_batches and self.all_cached_inventory:
                for item in self.all_cached_inventory:
                    if item['barcode'] == barcode:
                        self.loaded_batches.append({
                            "id": item["id"],
                            "medicine_name": item["name"],
                            "expiry_date": item["expiry"],
                            "current_quantity": item["qty"],
                            "batch_number": item["batch"]
                        })

            if not self.loaded_batches:
                QMessageBox.warning(self, "No Stock ❌", f"No active medicine found for lookup identity: {barcode}")
                return

            self.med_name_title.setText(f"Medicine: {self.loaded_batches[0]['medicine_name']}")
            total_pills = sum(int(b['current_quantity']) for b in self.loaded_batches)
            self.total_stock_lbl.setText(f"Total Stock Available: {total_pills} Pills")

            for idx, b in enumerate(self.loaded_batches):
                item_text = f"Batch ID: {b['batch_number']} | Expiry Date: {b['expiry_date']} -> ({b['current_quantity']} Pills)"
                if idx == 0 and int(b['current_quantity']) > 0:
                    item_text += "  ⭐ [Expires First]"
                item = QListWidgetItem(item_text)
                self.stock_list_widget.addItem(item)

            self.internal_stack.setCurrentIndex(1)
            self.handle_input_focus(self.quantity_input, None)

        except Exception as e:
            print(f"Error loading batches securely: {e}")

    def execute_smart_dispense(self):
        qty_str = self.quantity_input.text().strip()
        if not qty_str: return

        try:
            requested_qty = int(qty_str)
            if requested_qty <= 0: return

            total_available = sum(b["current_quantity"] for b in self.loaded_batches)
            if requested_qty > total_available:
                QMessageBox.critical(self, "Insufficient Stock ❌",
                                     f"You requested {requested_qty} pills, but stock only has {total_available}!")
                return

            confirm = QMessageBox.question(self, "Confirm Dispense ⚡",
                                           f"Are you sure you want to deduct {requested_qty} pills?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes: return

            remaining_to_deduct = requested_qty
            for batch in self.loaded_batches:
                if remaining_to_deduct <= 0: break
                if batch["current_quantity"] <= 0: continue

                if batch["current_quantity"] >= remaining_to_deduct:
                    new_qty = batch["current_quantity"] - remaining_to_deduct
                    airtable_api.update_medication_quantity(batch["id"], new_qty)
                    remaining_to_deduct = 0
                else:
                    remaining_to_deduct -= batch["current_quantity"]
                    airtable_api.update_medication_quantity(batch["id"], 0)

            airtable_api.log_transaction("DISPENSE", self.scanned_barcode, self.user_full_name, requested_qty,
                                         "Prescription Dispense")
            QMessageBox.information(self, "Success ✅", f"Successfully dispensed {requested_qty} pills.")
            self.kb_card_s2.hide()
            self.preload_inventory_cache()
            self.internal_stack.setCurrentIndex(0)
            self.clear_page()
        except ValueError:
            QMessageBox.warning(self, "Type Error ⚠️", "Quantity must be a valid number.")

    def clear_page(self):
        self.search_input.clear()
        self.quantity_input.clear()
        self.stock_list_widget.clear()
        self.live_matches_list.clear()
        self.scanned_barcode = ""
        self.loaded_batches = []
        self.kb_card.hide()
        self.kb_card_s2.hide()
        self.internal_stack.setCurrentIndex(0)