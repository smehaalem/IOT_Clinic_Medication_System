import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QHeaderView, QCheckBox, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
import airtable_api


class DispenseMedicationPage(QWidget):
    """
    Advanced Medication Dispensing Core Workspace.
    Supports dynamic Hybrid FIFO calculations, explicit batch selection, tabular UX layouts,
    and optimized touchscreen scroll behaviors with enhanced large text visibility.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.user_role = "User"
        self.user_full_name = "System User"
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

        # 🔥 Preload cloud database catalog directly upon widget instance initialization
        self.preload_inventory_cache()

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
                qty = airtable_api.safe_extract(fields.get("Current Pills Count"), int) or airtable_api.safe_extract(
                    fields.get("Quantity"), int) or 0

                if qty > 0:
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
                        "dosage": airtable_api.safe_extract(fields.get("Dosage"), str) or airtable_api.safe_extract(
                            fields.get("Strength"), str) or "N/A",
                        "qty": qty,
                        "batch": airtable_api.safe_extract(fields.get("A Batch"), str) or airtable_api.safe_extract(
                            fields.get("Batch Number"), str) or "N/A",
                        "expiry": airtable_api.safe_extract(fields.get("Expiry Date"), str)
                    })

            # 🔥 Populate the main summary master table immediately after completing the fetch loop
            self.run_live_filter()
        except Exception as e:
            print(f"⚠️ Stock cache bypass log: {e}")

    # =====================================================================
    # 🎴 SCREEN 0: Live Search & Scanner Entry Layout (Large Readable Text)
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

        search_type_layout = QHBoxLayout()
        lbl = QLabel("Filter Criteria:")
        lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #475569;")
        search_type_layout.addWidget(lbl)

        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Barcode", "Medicine Name", "Active Ingredient", "Batch ID"])
        self.search_type_combo.setStyleSheet("""
            QComboBox { padding: 8px 12px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; background-color: #FFFFFF; color: #1E293B; min-width: 150px; }
        """)
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)
        search_type_layout.addWidget(self.search_type_combo)
        search_type_layout.addStretch()
        left_layout.addLayout(search_type_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode identity or type to live query search...")
        self.search_input.setStyleSheet(
            "padding: 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px;")
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.returnPressed.connect(self.handle_scanner_return_pressed)
        left_layout.addWidget(self.search_input)

        self.live_matches_list = QTableWidget()
        self.live_matches_list.setColumnCount(3)
        self.live_matches_list.setHorizontalHeaderLabels(["Medication Name", "Strength", "Barcode"])
        self.live_matches_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.live_matches_list.setEditTriggers(QTableWidget.NoEditTriggers)

        self.live_matches_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.live_matches_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.live_matches_list.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        self.live_matches_list.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; background: #F8FAFC; font-size: 14px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; color: #475569; border: none; padding: 8px; font-size: 14px; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 12px; margin: 0px; border-radius: 6px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 30px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        self.live_matches_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.live_matches_list.verticalHeader().setDefaultSectionSize(36)
        self.live_matches_list.itemClicked.connect(self.handle_table_row_selection)
        left_layout.addWidget(self.live_matches_list)

        main_layout.addWidget(left_card)
        self.internal_stack.addWidget(page)

    # =====================================================================
    # 🎴 SCREEN 1: Grid Table Selection Board (Large Readable Text)
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
        self.med_name_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4F46E5;")
        form_layout.addWidget(self.med_name_title)

        self.total_stock_lbl = QLabel("Total Inventory Count: --")
        self.total_stock_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")
        form_layout.addWidget(self.total_stock_lbl)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels(["Select", "Batch ID", "Expiry Date", "Stock Qty", "Status"])
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.batch_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.batch_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.batch_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        self.batch_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; font-size: 14px; background-color: #FFFFFF; }
            QHeaderView::section { background-color: #F8FAFC; font-weight: bold; padding: 6px; color: #475569; font-size: 14px; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 12px; margin: 0px; border-radius: 6px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 30px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.batch_table.verticalHeader().setDefaultSectionSize(36)
        form_layout.addWidget(self.batch_table)

        form_layout.addWidget(
            QLabel("Required Pills / Dosage Count:", styleSheet="font-size: 13px; font-weight: bold; color: #475569;"))
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Type pill count to dispense...")
        self.quantity_input.setStyleSheet(
            "padding: 10px; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 6px; background-color: #F8FAFC;")
        form_layout.addWidget(self.quantity_input)

        self.dispense_btn = QPushButton("⚡ Confirm & Run Hybrid FIFO Allocation")
        self.dispense_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.dispense_btn.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.dispense_btn.clicked.connect(self.execute_smart_dispense)
        form_layout.addWidget(self.dispense_btn)

        nav_layout = QHBoxLayout()
        another_btn = QPushButton("🔄 Scan New Identity")
        another_btn.setCursor(QCursor(Qt.PointingHandCursor))
        another_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 10px; font-size: 13px; font-weight: bold; border-radius: 6px; border: 1px solid #E2E8F0;")
        another_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))

        finish_btn = QPushButton("🏁 Complete")
        finish_btn.setCursor(QCursor(Qt.PointingHandCursor))
        finish_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; padding: 10px; font-size: 13px; font-weight: bold; border-radius: 6px; border: none;")
        finish_btn.clicked.connect(self.clear_page)
        finish_btn.clicked.connect(self.on_back_to_menu)

        nav_layout.addWidget(another_btn, stretch=1)
        nav_layout.addWidget(finish_btn, stretch=1)
        form_layout.addLayout(nav_layout)

        main_layout.addWidget(form_card)
        self.internal_stack.addWidget(page)

    # =====================================================================
    # ⚙️ INTERACTIVE INTERFACE LOGIC & DATA PARSING
    # =====================================================================
    def handle_input_focus(self, input_field, event):
        for box in [self.search_input, self.quantity_input]:
            box.setStyleSheet(
                "padding: 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; background-color: #F8FAFC; color: #1E293B;")
        if event: super(QLineEdit, input_field).focusInEvent(event)
        input_field.setStyleSheet(
            "padding: 10px; border: 2px solid #6366F1; border-radius: 6px; font-size: 14px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")

    def run_live_filter(self):
        """ Fully optimized filter matching text dynamically with default master state recovery """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()
        self.live_matches_list.setRowCount(0)

        if not self.all_cached_inventory: return

        matched_items = []
        # 🔥 إذا كانت خانة البحث فارغة، يتم عرض جميع أدوية الكاش مباشرة كمظهر افتراضي مستقر
        if not search_text:
            matched_items = self.all_cached_inventory
        else:
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

                if search_text in str(val_to_check).lower():
                    matched_items.append(med)

        # دمج الأدوية التي تمتلك نفس الباركود لتجنب تكرار الصفوف بصرياً في شبكة البحث الأولية
        seen_barcodes = set()
        row_idx = 0
        for med in matched_items:
            clean_b = med['barcode'] or "NO_BARCODE"

            if isinstance(clean_b, dict):
                clean_b = clean_b.get('text', '')
            elif str(clean_b).startswith("{'text':"):
                try:
                    import ast
                    parsed_dict = ast.literal_eval(str(clean_b))
                    clean_b = parsed_dict.get('text', clean_b)
                except Exception:
                    pass

            # تجميع بصري فريد
            dedup_key = f"{med['name'].lower()}_{clean_b.lower()}"
            if dedup_key not in seen_barcodes:
                seen_barcodes.add(dedup_key)
                self.live_matches_list.insertRow(row_idx)

                name_item = QTableWidgetItem(med["name"])
                dosage_item = QTableWidgetItem(med["dosage"])
                barcode_item = QTableWidgetItem(str(clean_b))

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
            self.process_barcode_routing(explicit_barcode=barcode)

    def handle_table_row_selection(self, item):
        row = item.row()
        name_item = self.live_matches_list.item(row, 0)
        barcode = name_item.data(Qt.UserRole)
        if barcode:
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
            self.quantity_input.setFocus()

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

            selected_batches = []
            for row in range(self.batch_table.rowCount()):
                chk_widget = self.batch_table.cellWidget(row, 0)
                if chk_widget:
                    chk = chk_widget.findChild(QCheckBox)
                    if chk and chk.isChecked():
                        batch_data = self.batch_table.item(row, 1).data(Qt.UserRole)
                        selected_batches.append(batch_data)

            is_explicit_mode = len(selected_batches) > 0
            pool_to_calculate = selected_batches if is_explicit_mode else self.loaded_batches

            total_available_in_pool = sum(int(b["current_quantity"]) for b in pool_to_calculate)
            if requested_qty > total_available_in_pool:
                pool_name = "the selected boxes" if is_explicit_mode else "total active stock"
                QMessageBox.critical(self, "Insufficient Stock Count ❌",
                                     f"Requested {requested_qty} pills, but {pool_name} only contains {total_available_in_pool} available!")
                return

            pool_to_calculate.sort(key=lambda x: x["expiry_date"])

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

                allocation_report.append(f"• Expiry [ {batch['expiry_date']} ] : Take exactly {pills_to_draw} pills.")
                execution_plan.append({"id": batch["id"], "old_qty": current_qty, "drawn": pills_to_draw})

            report_msg = "🎯 Medication Allocation Draw Strategy:\n\n" + "\n".join(allocation_report)
            confirm = QMessageBox.question(self, "Confirm Secure Allocation Draw ⚡",
                                           report_msg + "\n\nDo you authorize this cloud inventory deduction?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes: return

            # 🩺 שילוב חלון קלט קופץ חסום (Validation Loop) להזנת שם הרופא באנגלית
            doctor_name = ""
            while True:
                text, ok = QInputDialog.getText(
                    self,
                    "Physician Authorization Required",
                    "Who is the doctor that issued the medication?\n(Please provide full name):"
                )
                if ok and text.strip():
                    doctor_name = text.strip()
                    break
                else:
                    QMessageBox.warning(
                        self,
                        "Required Field ⚠️",
                        "Doctor Name cannot be empty! You must fill this field to complete the operation."
                    )

            # עדכון כמויות ב-Airtable עבור כל המנות שחושבו
            for plan in execution_plan:
                new_qty = plan["old_qty"] - plan["drawn"]
                airtable_api.update_medication_quantity(plan["id"], new_qty)

            log_note = "Dispensed to Patient"

            # 🔥 קריאה לפונקציית ה-API המעודכנת: מעבירה את שם הרופא בנפרד לשדה "Doctor" בענן
            airtable_api.log_transaction(
                "DISPENSE",
                self.scanned_barcode,
                self.user_full_name,  # נשמר ב-Action By User המקורי ללא שינוי
                requested_qty,
                log_note,
                doctor_name=doctor_name  # נשלח ישירות לפרמטר החדש בעמודה הנפרדת
            )

            QMessageBox.information(self, "Transaction Approved ✅",
                                    f"Successfully processed {requested_qty} pills using Hybrid Allocation.")
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
        self.internal_stack.setCurrentIndex(0)

        # 🔥 Refresh default list rendering state automatically on exit contexts
        self.preload_inventory_cache()
        self.search_input.setFocus()