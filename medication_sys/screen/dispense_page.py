import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QHeaderView, QCheckBox
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


class DispenseMedicationPage(QWidget):
    """
    Advanced Medication Dispensing Core Workspace.
    Supports dynamic Hybrid FIFO calculations, explicit batch selection, tabular UX layouts,
    and fully targets the 'Barcode lookup' fields.
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
        """ Pulls inventory and unpacks the Barcode lookup field list structure """
        self.all_cached_inventory = []
        try:
            if not hasattr(airtable_api, 'stock_table') or airtable_api.stock_table is None:
                return
            records = airtable_api.stock_table.all()
            if not records: return

            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                qty = airtable_api.safe_extract(fields.get("Current Pills Count"), int)
                if qty > 0:
                    # 🔥 Targeted: Extracting dynamically from Barcode lookup field
                    raw_b = fields.get("Barcode lookup") or fields.get("Barcode", "")
                    if isinstance(raw_b, list):
                        clean_b = str(raw_b[0]).strip() if raw_b else ""
                    else:
                        clean_b = str(raw_b).strip()

                    self.all_cached_inventory.append({
                        "id": r.id if hasattr(r, 'id') else r.get('id'),
                        "name": airtable_api.safe_extract(fields.get("Medicine Name"), str),
                        "barcode": clean_b,
                        "ingredient": airtable_api.safe_extract(fields.get("Active Ingredient"), str),
                        "dosage": airtable_api.safe_extract(fields.get("Dosage"), str),
                        "qty": qty,
                        "batch": airtable_api.safe_extract(fields.get("A Batch"), str),
                        "expiry": airtable_api.safe_extract(fields.get("Expiry Date"), str)
                    })
        except Exception as e:
            print(f"⚠️ Stock cache bypass log: {e}")

    # =====================================================================
    # 🎴 SCREEN 0: Live Search & Scanner Entry Layout
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
        title = QLabel("📦 Dispense Medication Workspace")
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
        lbl = QLabel("Filter Criteria:")
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
        self.search_input.setPlaceholderText("Scan barcode identity or type to live query search...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px;")
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.returnPressed.connect(self.handle_scanner_return_pressed)

        self.search_input.focusInEvent = lambda event: self.handle_input_focus(self.search_input, event)
        self.search_input.installEventFilter(self)
        left_layout.addWidget(self.search_input)

        self.live_matches_list = QTableWidget()
        self.live_matches_list.setColumnCount(3)
        self.live_matches_list.setHorizontalHeaderLabels(["Medication Name", "Strength", "Barcode"])
        self.live_matches_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.live_matches_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.live_matches_list.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; background: #F8FAFC; font-size: 12px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; color: #475569; border: none; padding: 6px; }
        """)
        self.live_matches_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.live_matches_list.itemClicked.connect(self.handle_table_row_selection)
        left_layout.addWidget(self.live_matches_list)

        main_layout.addWidget(left_card, stretch=5)

        # ⌨️ Embedded Touch Input Pad
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
    # 🎴 SCREEN 1: Grid Table Selection Board
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

        self.med_name_title = QLabel("Medicine Name: Loading...")
        self.med_name_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4F46E5;")
        form_layout.addWidget(self.med_name_title)

        self.total_stock_lbl = QLabel("Total Inventory Count: --")
        self.total_stock_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #2563EB;")
        form_layout.addWidget(self.total_stock_lbl)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels(["Select", "Batch ID", "Expiry Date", "Stock Qty", "Status"])
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; font-size: 11px; background-color: #FFFFFF; }
            QHeaderView::section { background-color: #F8FAFC; font-weight: bold; padding: 5px; color: #475569; }
        """)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        form_layout.addWidget(self.batch_table)

        form_layout.addWidget(
            QLabel("Required Pills / Dosage Count:", styleSheet="font-size: 11px; font-weight: bold; color: #475569;"))
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Type pill count to dispense...")
        self.quantity_input.setStyleSheet(
            "padding: 8px; font-size: 12px; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event)
        self.quantity_input.installEventFilter(self)
        form_layout.addWidget(self.quantity_input)

        self.dispense_btn = QPushButton("⚡ Confirm & Run Hybrid FIFO Allocation")
        self.dispense_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.dispense_btn.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.dispense_btn.clicked.connect(self.execute_smart_dispense)
        form_layout.addWidget(self.dispense_btn)

        nav_layout = QHBoxLayout()
        another_btn = QPushButton("🔄 Scan New Identity")
        another_btn.setCursor(QCursor(Qt.PointingHandCursor))
        another_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 8px; font-size: 12px; font-weight: bold; border-radius: 6px; border: 1px solid #E2E8F0;")
        another_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))

        finish_btn = QPushButton("🏁 Complete")
        finish_btn.setCursor(QCursor(Qt.PointingHandCursor))
        finish_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; padding: 8px; font-size: 12px; font-weight: bold; border-radius: 6px; border: none;")
        finish_btn.clicked.connect(self.clear_page)
        finish_btn.clicked.connect(self.on_back_to_menu)

        nav_layout.addWidget(another_btn, stretch=1)
        nav_layout.addWidget(finish_btn, stretch=1)
        form_layout.addLayout(nav_layout)

        main_layout.addWidget(form_card, stretch=5)

        # 🧮 Numerical Pad Frame Container
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
    # ⚙️ INTERACTIVE INTERFACE LOGIC & DATA PARSING
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
        """ Fully optimized filter matching text against sanitized real barcodes using lookup structures """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()
        self.live_matches_list.setRowCount(0)

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
        row_idx = 0
        for med in matched_items:
            clean_b = med['barcode']

            # 🔥 Fix: Extract clean value if the barcode comes wrapped as a dictionary string or object
            if isinstance(clean_b, dict):
                clean_b = clean_b.get('text', '')
            elif str(clean_b).startswith("{'text':"):
                # Fallback string parsing just in case it's treated as raw unparsed text
                try:
                    import ast
                    parsed_dict = ast.literal_eval(str(clean_b))
                    clean_b = parsed_dict.get('text', clean_b)
                except Exception:
                    pass

            if clean_b not in seen_barcodes:
                seen_barcodes.add(clean_b)
                self.live_matches_list.insertRow(row_idx)

                name_item = QTableWidgetItem(med["name"])
                dosage_item = QTableWidgetItem(med["dosage"])
                barcode_item = QTableWidgetItem(str(clean_b))  # Safely renders clean digits

                name_item.setData(Qt.UserRole, clean_b)

                self.live_matches_list.setItem(row_idx, 0, name_item)
                self.live_matches_list.setItem(row_idx, 1, dosage_item)
                self.live_matches_list.setItem(row_idx, 2, barcode_item)
                row_idx += 1

    def handle_scanner_return_pressed(self):
        barcode = self.search_input.text().strip()
        if barcode:
            if self.live_matches_list.rowCount() > 0:
                best_item = self.live_matches_list.item(0, 0)
                barcode = best_item.data(Qt.UserRole)
            self.kb_card.hide()
            self.process_barcode_routing(explicit_barcode=barcode)

    def handle_table_row_selection(self, item):
        row = item.row()
        name_item = self.live_matches_list.item(row, 0)
        barcode = name_item.data(Qt.UserRole)
        if barcode:
            self.kb_card.hide()
            self.process_barcode_routing(explicit_barcode=barcode)

    def process_barcode_routing(self, explicit_barcode=None):
        """ Pulls batches and completely tracks against Barcode lookup arrays """
        barcode = explicit_barcode or self.search_input.text().strip()
        if not barcode: return
        barcode = str(barcode).strip()

        self.scanned_barcode = barcode
        self.batch_table.setRowCount(0)

        try:
            self.loaded_batches = airtable_api.find_all_batches_by_barcode(barcode)

            # Local fallback synchronization
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
                QMessageBox.warning(self, "No Stock ❌", f"No medication records found matching code: {barcode}")
                return

            self.med_name_title.setText(f"Medication Type: {self.loaded_batches[0]['medicine_name']}")
            total_pills = sum(int(b['current_quantity']) for b in self.loaded_batches)
            self.total_stock_lbl.setText(f"Total Available Cloud Count: {total_pills} Pills")

            for idx, b in enumerate(self.loaded_batches):
                self.batch_table.insertRow(idx)

                chk_widget = QWidget()
                chk_layout = QHBoxLayout(chk_widget)
                chk_layout.setContentsMargins(0, 0, 0, 0)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk = QCheckBox()
                chk_layout.addWidget(chk)
                self.batch_table.setCellWidget(idx, 0, chk_widget)

                batch_item = QTableWidgetItem(str(b['batch_number']))
                expiry_item = QTableWidgetItem(str(b['expiry_date']))
                qty_item = QTableWidgetItem(str(b['current_quantity']))
                status_item = QTableWidgetItem("⭐ Expires First" if idx == 0 else "Normal")

                batch_item.setData(Qt.UserRole, b)

                self.batch_table.setItem(idx, 1, batch_item)
                self.batch_table.setItem(idx, 2, expiry_item)
                self.batch_table.setItem(idx, 3, qty_item)
                self.batch_table.setItem(idx, 4, status_item)

            self.internal_stack.setCurrentIndex(1)
            self.handle_input_focus(self.quantity_input, None)

        except Exception as e:
            print(f"Error packing selection grid tables: {e}")

    # =====================================================================
    # 🧠 HYBRID FIFO ALLOCATION ENGINE
    # =====================================================================
    def execute_smart_dispense(self):
        qty_str = self.quantity_input.text().strip()
        if not qty_str: return

        try:
            requested_qty = int(qty_str)
            if requested_qty <= 0: return

            # 1. Gather batches explicitly checked by user
            selected_batches = []
            for row in range(self.batch_table.rowCount()):
                chk_widget = self.batch_table.cellWidget(row, 0)
                if chk_widget:
                    chk = chk_widget.findChild(QCheckBox)
                    if chk and chk.isChecked():
                        batch_data = self.batch_table.item(row, 1).data(Qt.UserRole)
                        selected_batches.append(batch_data)

            # 2. Determine target calculation workspace pool
            is_explicit_mode = len(selected_batches) > 0
            pool_to_calculate = selected_batches if is_explicit_mode else self.loaded_batches

            # Run safety capacity check on the focused pool
            total_available_in_pool = sum(int(b["current_quantity"]) for b in pool_to_calculate)
            if requested_qty > total_available_in_pool:
                pool_name = "the selected boxes" if is_explicit_mode else "total active stock"
                QMessageBox.critical(self, "Insufficient Stock Count ❌",
                                     f"Requested {requested_qty} pills, but {pool_name} only contains {total_available_in_pool} available!")
                return

            # Enforce strict timestamp sorting for perfect FIFO execution
            pool_to_calculate.sort(key=lambda x: x["expiry_date"])

            # 3. Simulate FIFO depletion matrix mapping
            remaining_to_deduct = requested_qty
            allocation_report = []
            execution_plan = []

            for batch in pool_to_calculate:
                if remaining_to_deduct <= 0: break
                current_qty = int(batch["current_quantity"])
                if current_qty <= 0: continue

                if current_qty >= remaining_to_deduct:
                    pills_to_draw = remaining_to_deduct
                    remaining_to_deduct = 0
                else:
                    pills_to_draw = current_qty
                    remaining_to_deduct -= current_qty

                # 🔥 Formats strategy report by Expiry Date to be intuitive for staff
                allocation_report.append(f"• Expiry [ {batch['expiry_date']} ] : Take exactly {pills_to_draw} pills.")
                execution_plan.append({"id": batch["id"], "old_qty": current_qty, "drawn": pills_to_draw})

            # 4. Display confirmation visualization dialog report
            report_msg = "🎯 Medication Allocation Draw Strategy:\n\n" + "\n".join(allocation_report)
            confirm = QMessageBox.question(self, "Confirm Secure Allocation Draw ⚡",
                                           report_msg + "\n\nDo you authorize this cloud inventory deduction?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes: return

            # 5. Commit mutations live to cloud database
            for plan in execution_plan:
                new_qty = plan["old_qty"] - plan["drawn"]
                airtable_api.update_medication_quantity(plan["id"], new_qty)

            # Log transaction footprint securely
            log_note = "Explicit Batch Multi-Select Draw" if is_explicit_mode else "Full-pool Automatic FIFO Draw"
            airtable_api.log_transaction("DISPENSE", self.scanned_barcode, self.user_full_name, requested_qty, log_note)

            QMessageBox.information(self, "Transaction Approved ✅",
                                    f"Successfully processed {requested_qty} pills using Hybrid Allocation.")
            self.kb_card_s2.hide()
            self.preload_inventory_cache()
            self.internal_stack.setCurrentIndex(0)
            self.clear_page()

        except ValueError:
            QMessageBox.warning(self, "Data Type Error ⚠️", "Please enter a valid integer for required count.")

    def clear_page(self):
        self.search_input.clear()
        self.quantity_input.clear()
        self.batch_table.setRowCount(0)
        self.live_matches_list.setRowCount(0)
        self.scanned_barcode = ""
        self.loaded_batches = []
        self.kb_card.hide()
        self.kb_card_s2.hide()
        self.internal_stack.setCurrentIndex(0)