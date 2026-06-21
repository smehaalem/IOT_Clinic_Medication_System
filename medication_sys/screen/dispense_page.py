import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QListWidget, QListWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
import airtable_api


class DispenseMedicationPage(QWidget):
    """
    Highly Intuitive Medication Dispensing Screen.
    Features dynamic touch keyboard auto-toggling, multi-field live search,
    and crystal clear direct clinic layout.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.user_role = "User"
        self.user_full_name = "System User"
        self.current_focused_input = None
        self.scanned_barcode = ""
        self.loaded_batches = []
        self.all_cached_inventory = []  # ذاكرة مؤقتة لفلترة الأدوية لايف وسريعاً بدون تعليق السيرفر

        self.internal_stack = QStackedWidget(self)

        self.init_scan_screen()  # Index 0
        self.init_selection_screen()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

    def set_user_session(self, role, full_name):
        """ تحديث بيانات المستخدم وتجهيز الذاكرة المؤقتة للأدوية """
        self.user_role = str(role).strip().lower()
        self.user_full_name = str(full_name).strip()
        self.update_purge_button_visibility()
        self.preload_inventory_cache()  # تحميل المخزون لايف فور فتح الصفحة للبحث السريع

    def update_purge_button_visibility(self):
        if self.user_role == "maneger" and self.loaded_batches:
            self.purge_btn.show()
        else:
            self.purge_btn.hide()

    def preload_inventory_cache(self):
        """ جلب أولي للمخزون لتوفير فلترة فورية (Live Search) بدون أي تأخير """
        try:
            # جلب السجلات المخزنة حالياً بسيرفر العيادة
            records = airtable_api.stock_table.all()
            self.all_cached_inventory = []
            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                qty = int(fields.get("Current Pills Count", 0))
                if qty > 0:  # لا نعرض الأدوية التي كميتها 0 حبة كما صلحنا سابقاً
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
            print(f"Error caching stock: {e}")

    # =====================================================================
    # 🎴 SCREEN 0: Dynamic Live Search & Scan Screen
    # =====================================================================
    def init_scan_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("📦 Dispense Medicine")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A; border: none;")

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "padding: 6px 14px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; color: #475569; border: 1px solid #E2E8F0;")
        back_btn.clicked.connect(self.clear_page)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        # 🎯 السهم الصغير الذكي لاختيار طريقة البحث المطلوبة بكل بساطة
        search_type_layout = QHBoxLayout()
        search_type_layout.addWidget(QLabel("Search Method:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Medicine Name", "Barcode", "Active Ingredient"])
        self.search_type_combo.setStyleSheet(
            "padding: 8px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 13px; min-width: 150px;")
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)  # إعادة الفلترة فوراً عند تغيير النوع
        search_type_layout.addWidget(self.search_type_combo)
        search_type_layout.addStretch()
        left_layout.addLayout(search_type_layout)

        left_layout.addWidget(QLabel("Type to Search Inventory Live:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Start typing to filter results instantly...")
        self.search_input.setStyleSheet(
            "padding: 14px; border: 2px solid #CBD5E1; border-radius: 10px; font-size: 14px;")

        # ⚡ ربط الإدخال بالبحث الحي (Live Search) والاكتشاف التلقائي لفوكس الكيبورد
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.focusInEvent = lambda event: self.handle_input_focus(self.search_input, event, show_kb=True)
        self.search_input.focusOutEvent = lambda event: self.handle_input_focus(self.search_input, event, show_kb=False)
        left_layout.addWidget(self.search_input)

        # 📋 قائمة عرض نتائج البحث الفورية والذكية باللمس
        left_layout.addWidget(QLabel("Matches Found (Click to open):"))
        self.live_matches_list = QListWidget()
        self.live_matches_list.setStyleSheet(
            "border: 1px solid #E2E8F0; border-radius: 10px; background: #F8FAFC; font-size: 13px; padding: 5px;")
        self.live_matches_list.itemClicked.connect(self.handle_live_item_selection)
        left_layout.addWidget(self.live_matches_list)

        main_layout.addWidget(left_card, stretch=5)

        # ⌨️ الكيبورد الذكي الديناميكي الجانبي (مخفي برمجياً بالبداية لتوفير المساحة)
        self.kb_card = QFrame()
        self.kb_card.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(self.kb_card)
        kb_layout.addWidget(QLabel("Touch Entry Pad:"))

        keyboard_widget = QWidget()
        keyboard_lay = QVBoxLayout(keyboard_widget)
        keyboard_lay.setContentsMargins(0, 0, 0, 0)
        keyboard_lay.setSpacing(4)
        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            [' ', 'Clear', '⌫']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(
                    "background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 14px 6px; border-radius: 6px; border: 1px solid #E2E8F0;")
                if key in ['Clear', '⌫']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 14px 6px; border-radius: 6px; border: none;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 14px 6px; border-radius: 6px; min-width: 80px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            keyboard_lay.addLayout(r_lay)
        kb_layout.addWidget(keyboard_widget)
        kb_layout.addStretch()

        main_layout.addWidget(self.kb_card, stretch=4)
        self.kb_card.hide()  # 🔥 إخفاء الكيبورد في البداية ليكون التخطيط مريحاً للعين وعريضاً!

        self.internal_stack.addWidget(page)

    # =====================================================================
    # 📝 SCREEN 1: Multi-Batch Selection & Dispense (No Keyboard Needed)
    # =====================================================================
    def init_selection_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        form_card = QFrame()
        form_card.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(6)

        self.med_name_title = QLabel("Medicine: Loading...")
        self.med_name_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        form_layout.addWidget(self.med_name_title)

        self.total_stock_lbl = QLabel("Total Available: -- Pills")
        self.total_stock_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB; margin-bottom: 5px;")
        form_layout.addWidget(self.total_stock_lbl)

        form_layout.addWidget(QLabel("Available Batches in Stock:"))
        self.stock_list_widget = QListWidget()
        self.stock_list_widget.setStyleSheet("border: 1px solid #E2E8F0; border-radius: 8px; background: #F8FAFC;")
        form_layout.addWidget(self.stock_list_widget)

        form_layout.addWidget(QLabel("Pills to Dispense (Quantity):"))
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter number of pills...")
        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event,
                                                                                 show_kb=True)
        form_layout.addWidget(self.quantity_input)

        self.dispense_btn = QPushButton("⚡ Confirm & Dispense Now")
        self.dispense_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.dispense_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px;")
        self.dispense_btn.clicked.connect(self.execute_smart_dispense)
        form_layout.addWidget(self.dispense_btn)

        self.purge_btn = QPushButton("🗑️ Manager Option: Delete This Batch From Storage")
        self.purge_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.purge_btn.setStyleSheet(
            "background-color: #EF4444; color: white; padding: 10px; font-weight: bold; border-radius: 8px; border: none; font-size: 13px; margin-top: 2px;")
        self.purge_btn.clicked.connect(self.execute_manager_purge)
        self.purge_btn.hide()
        form_layout.addWidget(self.purge_btn)

        nav_layout = QHBoxLayout()
        another_btn = QPushButton("🔄 Scan Another Product")
        another_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 10px; font-weight: bold; border-radius: 8px; border: 1px solid #E2E8F0;")
        another_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))

        finish_btn = QPushButton("🏁 Finish & Go Back")
        finish_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; padding: 10px; font-weight: bold; border-radius: 8px; border: none;")
        finish_btn.clicked.connect(self.clear_page)
        finish_btn.clicked.connect(self.on_back_to_menu)

        nav_layout.addWidget(another_btn)
        nav_layout.addWidget(finish_btn)
        form_layout.addLayout(nav_layout)

        main_layout.addWidget(form_card, stretch=5)

        # ربط الكيبورد اللمسي بالشاشة الثانية بشكل ديناميكي أيضاً
        self.kb_card_s2 = QFrame()
        self.kb_card_s2.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        kb_lay2 = QVBoxLayout(self.kb_card_s2)
        kb_lay2.addWidget(QLabel("Numeric Entry Pad:"))
        num_grid2 = QVBoxLayout()
        rows2 = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['Clear', '0', '⌫']]
        for r in rows2:
            rl = QHBoxLayout()
            for key in r:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(
                    "background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 16px 0; border-radius: 8px; border: 1px solid #E2E8F0;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                rl.addWidget(btn)
            num_grid2.addLayout(rl)
        kb_lay2.addLayout(num_grid2)
        kb_lay2.addStretch()
        main_layout.addWidget(self.kb_card_s2, stretch=4)
        self.kb_card_s2.hide()

        self.internal_stack.addWidget(page)

    # =====================================================================
    # ⚙️ INTERACTIVE UX & LIVE FILTERING CONTROLS
    # =====================================================================
    def handle_input_focus(self, input_field, event, show_kb=True):
        """ إضاءة الحقل المحدد والتحكم التلقائي الديناميكي في ظهور واختفاء الكيبورد """
        for box in [self.search_input, self.quantity_input]:
            box.setStyleSheet(
                "padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 13px; background-color: #F8FAFC;")

        self.current_focused_input = input_field

        # إظهار أو إخفاء الكيبورد التابع للصفحة المفتوحة ديناميكياً لتوسيع العرض
        if self.internal_stack.currentIndex() == 0:
            if show_kb: self.kb_card.show()
        else:
            if show_kb: self.kb_card_s2.show()

        input_field.setStyleSheet(
            "padding: 10px; border: 2px solid #EF4444; border-radius: 8px; font-size: 13px; background-color: #FEF2F2; color: #0F172A; font-weight: bold;")

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        else:
            self.current_focused_input.setText(current_text + key)
        self.current_focused_input.setFocus(Qt.OtherFocusReason)

    def run_live_filter(self):
        """ الفلترة الحية واللحظية للأدوية (Live Search) مع كل حرف يكتبه المستخدم """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()
        self.live_matches_list.clear()

        if not search_text:
            return

        # فلترة الذاكرة المؤقتة لسرعة الاستجابة باللمس
        matched_items = []
        for med in self.all_cached_inventory:
            val_to_check = ""
            if search_type == "Medicine Name":
                val_to_check = med["name"].lower()
            elif search_type == "Barcode":
                val_to_check = med["barcode"].lower()
            elif search_type == "Active Ingredient":
                val_to_check = med["ingredient"].lower()

            if search_text in val_to_check:
                matched_items.append(med)

        # إزالة التكرار التجاري وعرض النتائج المتاحة بشكل منظم جداً
        seen_barcodes = set()
        for med in matched_items:
            if med["barcode"] not in seen_barcodes:
                seen_barcodes.add(med["barcode"])
                display_text = f"💊 {med['name']} | Strength: {med['dosage']} | (Barcode: {med['barcode']})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, med["barcode"])  # حفظ الباركود مخفياً بداخل العنصر
                self.live_matches_list.addItem(item)

    def handle_live_item_selection(self, item):
        """ الانتقال التلقائي للدفعات بمجرد كبس الموظف على الدواء من القائمة الحية """
        barcode = item.data(Qt.UserRole)
        if barcode:
            self.kb_card.hide()  # إخفاء كيبورد الشاشة الأولى تلقائياً
            self.process_barcode_routing(explicit_barcode=barcode)

    def process_barcode_routing(self, explicit_barcode=None):
        barcode = explicit_barcode or self.search_input.text().strip()
        if not barcode: return

        self.scanned_barcode = barcode
        self.stock_list_widget.clear()

        try:
            self.loaded_batches = airtable_api.find_all_batches_by_barcode(barcode)

            if not self.loaded_batches:
                QMessageBox.warning(self, "No Stock ❌", "No active medicine found for this product.")
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
            self.handle_input_focus(self.quantity_input, None, show_kb=True)

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
            self.preload_inventory_cache()  # تصفير وتحديث الذاكرة لايف فوراً
            self.internal_stack.setCurrentIndex(0)  # العودة السلسة لصفحة البحث
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