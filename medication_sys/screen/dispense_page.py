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
    Optimized for Barcode Scanner inputs and dynamic hidden touch keyboards.
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
        self.update_purge_button_visibility()
        self.preload_inventory_cache()

    def update_purge_button_visibility(self):
        if self.user_role == "maneger" and self.loaded_batches:
            self.purge_btn.show()
        else:
            self.purge_btn.hide()

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
                    self.all_cached_inventory.append({
                        "id": r.id if hasattr(r, 'id') else r.get('id'),
                        "name": fields.get("Medicine Name", ""),
                        "barcode": fields.get("Barcode", ""),
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
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        title = QLabel("📦 Dispense Medicine")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A; border: none;")

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

        search_type_layout = QHBoxLayout()
        lbl = QLabel("Search:")
        lbl.setStyleSheet("font-size: 11px;")
        search_type_layout.addWidget(lbl)
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Barcode", "Medicine Name", "Active Ingredient", "Batch ID"])
        self.search_type_combo.setStyleSheet(
            "padding: 5px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 11px; min-width: 120px;")
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)
        search_type_layout.addWidget(self.search_type_combo)
        search_type_layout.addStretch()
        left_layout.addLayout(search_type_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or type to search...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px;")
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.returnPressed.connect(self.handle_scanner_return_pressed)

        # ربط دالة الفوكس وتثبيت الفلتر لمنع الفتح التلقائي الأوتوماتيكي
        self.search_input.focusInEvent = lambda event: self.handle_input_focus(self.search_input, event)
        self.search_input.installEventFilter(self)
        left_layout.addWidget(self.search_input)

        self.live_matches_list = QListWidget()
        self.live_matches_list.setStyleSheet(
            "border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 11px;")
        self.live_matches_list.itemClicked.connect(self.handle_live_item_selection)
        left_layout.addWidget(self.live_matches_list)

        main_layout.addWidget(left_card, stretch=5)

        # كيبورد الشاشة الأولى مضغوط ليلائم شاشة الرازبري
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
            [' ', 'Clear', '⌫', '🔽']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(3)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(
                    "background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 10px 2px; font-size: 11px; border-radius: 4px; border: 1px solid #E2E8F0;")
                if key in ['Clear', '⌫', '🔽']:
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

        # 🔐 إخفاء الكيبورد بشكل افتراضي في البداية
        self.kb_card.hide()

        self.internal_stack.addWidget(page)

    def init_selection_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        form_card = QFrame()
        form_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(4)

        self.med_name_title = QLabel("Medicine: Loading...")
        self.med_name_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        form_layout.addWidget(self.med_name_title)

        self.total_stock_lbl = QLabel("Total Available: --")
        self.total_stock_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #2563EB;")
        form_layout.addWidget(self.total_stock_lbl)

        self.stock_list_widget = QListWidget()
        self.stock_list_widget.setStyleSheet(
            "border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 11px;")
        form_layout.addWidget(self.stock_list_widget)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter quantity...")
        self.quantity_input.setStyleSheet(
            "padding: 6px; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 6px;")

        # ربط دالة الفوكس وتثبيت الفلتر لشاشة الكمية
        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event)
        self.quantity_input.installEventFilter(self)
        form_layout.addWidget(self.quantity_input)

        self.dispense_btn = QPushButton("⚡ Confirm & Dispense Now")
        self.dispense_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 8px; font-weight: bold; border-radius: 6px; border: none; font-size: 12px;")
        self.dispense_btn.clicked.connect(self.execute_smart_dispense)
        form_layout.addWidget(self.dispense_btn)

        self.purge_btn = QPushButton("🗑️ Manager: Delete Batch")
        self.purge_btn.setStyleSheet(
            "background-color: #EF4444; color: white; padding: 6px; font-weight: bold; border-radius: 6px; border: none; font-size: 11px;")
        self.purge_btn.clicked.connect(self.execute_manager_purge)
        self.purge_btn.hide()
        form_layout.addWidget(self.purge_btn)

        nav_layout = QHBoxLayout()
        another_btn = QPushButton("🔄 Scan Another")
        another_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 6px; font-size: 11px; font-weight: bold; border-radius: 6px; border: 1px solid #E2E8F0;")
        another_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))

        finish_btn = QPushButton("🏁 Finish")
        finish_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; padding: 6px; font-size: 11px; font-weight: bold; border-radius: 6px; border: none;")
        finish_btn.clicked.connect(self.clear_page)
        finish_btn.clicked.connect(self.on_back_to_menu)

        nav_layout.addWidget(another_btn)
        nav_layout.addWidget(finish_btn)
        form_layout.addLayout(nav_layout)

        main_layout.addWidget(form_card, stretch=5)

        self.kb_card_s2 = QFrame()
        self.kb_card_s2.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_lay2 = QVBoxLayout(self.kb_card_s2)
        num_grid2 = QVBoxLayout()
        rows2 = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['Clear', '0', '⌫', '🔽']]
        for r in rows2:
            rl = QHBoxLayout()
            rl.setSpacing(3)
            for key in r:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(
                    "background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 12px 0; font-size: 12px; border-radius: 6px; border: 1px solid #E2E8F0;")
                if key in ['Clear', '⌫', '🔽']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 12px 0; font-size: 11px; border-radius: 6px; border: none;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                rl.addWidget(btn)
            num_grid2.addLayout(rl)
        kb_lay2.addLayout(num_grid2)
        kb_lay2.addStretch()
        main_layout.addWidget(self.kb_card_s2, stretch=4)

        # 🔐 إخفاء كيبورد الأرقام بشكل افتراضي أيضاً في البداية
        self.kb_card_s2.hide()

        self.internal_stack.addWidget(page)

    # =====================================================================
    # ⚙️ INTERACTIVE UX & LIVE FILTERING CONTROLS
    # =====================================================================
    def handle_input_focus(self, input_field, event):
        for box in [self.search_input, self.quantity_input]:
            box.setStyleSheet(
                "padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 13px; background-color: #F8FAFC;")

        self.current_focused_input = input_field
        if event:
            super(QLineEdit, input_field).focusInEvent(event)

        input_field.setStyleSheet(
            "padding: 10px; border: 2px solid #EF4444; border-radius: 8px; font-size: 13px; background-color: #FEF2F2; color: #0F172A; font-weight: bold;")

    def eventFilter(self, obj, event):
        # التقاط حدث الكبس أو اللمس الحقيقي بإصبع المستخدم لفتح لوحة المفاتيح التابعة فوراً
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
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()
        self.live_matches_list.clear()

        if not search_text or not self.all_cached_inventory:
            return

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

            if isinstance(val_to_check, list):
                val_to_check = val_to_check[0] if val_to_check else ""
            val_to_check = str(val_to_check).lower()

            if search_text in val_to_check:
                matched_items.append(med)

        seen_barcodes = set()
        for med in matched_items:
            clean_b = med['barcode'][0] if isinstance(med['barcode'], list) else med['barcode']
            if clean_b not in seen_barcodes:
                seen_barcodes.add(clean_b)
                display_text = f"💊 {med['name']} | Strength: {med['dosage']} | (Batch: {med['batch']})"
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
        barcode = explicit_barcode or self.search_input.text().strip()
        if not barcode: return

        if isinstance(barcode, list):
            barcode = barcode[0] if barcode else ""
        barcode = str(barcode).strip()

        self.scanned_barcode = barcode
        self.stock_list_widget.clear()

        try:
            self.loaded_batches = airtable_api.find_all_batches_by_barcode(barcode)

            if not self.loaded_batches:
                QMessageBox.warning(self, "No Stock ❌", "No active medicine found for this barcode.")
                self.update_purge_button_visibility()
                return

            self.med_name_title.setText(f"Medicine: {self.loaded_batches[0]['medicine_name']}")
            total_pills = sum(b['current_quantity'] for b in self.loaded_batches)
            self.total_stock_lbl.setText(f"Total Stock Available: {total_pills} Pills")

            for idx, b in enumerate(self.loaded_batches):
                item_text = f"Batch ID: {b['batch_number']} | Expiry Date: {b['expiry_date']} -> ({b['current_quantity']} Pills)"
                if idx == 0 and b['current_quantity'] > 0:
                    item_text += "  ⭐ [Expires First]"
                item = QListWidgetItem(item_text)
                self.stock_list_widget.addItem(item)

            self.update_purge_button_visibility()
            self.internal_stack.setCurrentIndex(1)
            # تركيز صامت على حقل الكمية دون فتح الكيبورد تلقائياً لراحة الستاف
            self.handle_input_focus(self.quantity_input, None)

        except Exception as e:
            print(f"Error loading batches: {e}")

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

            confirm = QMessageBox.question(
                self, "Confirm Dispense ⚡",
                f"Are you sure you want to deduct {requested_qty} pills from inventory?",
                QMessageBox.Yes | QMessageBox.No
            )
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

    def execute_manager_purge(self):
        if not self.loaded_batches: return

        target = self.loaded_batches[0]
        confirm = QMessageBox.critical(
            self, "Confirm Delete ⚠️",
            f"Are you sure you want to permanently delete Batch '{target['batch_number']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                if airtable_api.delete_medication_record(target["id"]):
                    airtable_api.log_transaction("PURGE_DELETE", self.scanned_barcode, self.user_full_name,
                                                 target["current_quantity"], "Manager Emergency Disposal")
                    QMessageBox.information(self, "Deleted 🗑️", "Medication batch removed from system.")
                    self.kb_card_s2.hide()
                    self.preload_inventory_cache()
                    self.internal_stack.setCurrentIndex(0)
                    self.clear_page()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to complete purge: {e}")

    def clear_page(self):
        self.search_input.clear()
        self.quantity_input.clear()
        self.stock_list_widget.clear()
        self.live_matches_list.clear()
        self.scanned_barcode = ""
        self.loaded_batches = []
        self.update_purge_button_visibility()
        self.kb_card.hide()
        self.kb_card_s2.hide()
        self.internal_stack.setCurrentIndex(0)