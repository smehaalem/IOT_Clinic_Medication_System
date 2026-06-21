import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QDateEdit, QSpinBox,
    QDialog, QListWidget
)

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QCursor
import airtable_api


class BatchSelectionDialog(QDialog):
    """ نافذة منبثقة ذكية تخير المستخدم بين تعديل دفعة قديمة أو إضافة دفعة جديدة """

    def __init__(self, batches, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Product Batches Detected")
        self.setFixedWidth(420)
        self.selected_batch = None
        self.action_type = None  # "edit" or "new"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Multiple Batches Found!")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0EA5E9;")
        layout.addWidget(title)

        layout.addWidget(QLabel(
            "We found existing batches for this barcode.\nSelect a batch to EDIT or choose to create a NEW one:"))

        self.list_widget = QListWidget()
        from PyQt5.QtWidgets import QListWidgetItem
        for b in batches:
            item_text = f"Batch: {b['batch_number']} | Exp: {b['expiry_date']} (📦 {b['current_quantity']} Pills)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, b)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️ Edit Selected Batch")
        edit_btn.setStyleSheet(
            "background-color: #EA580C; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none;")
        edit_btn.clicked.connect(self.on_edit_clicked)

        new_batch_btn = QPushButton("➕ Create New Batch")
        new_batch_btn.setStyleSheet(
            "background-color: #0D9488; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none;")
        new_batch_btn.clicked.connect(self.on_new_clicked)

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(new_batch_btn)
        layout.addLayout(btn_layout)

    def on_edit_clicked(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selection Required", "Please select a batch from the list to edit.")
            return
        self.selected_batch = current_item.data(Qt.UserRole)
        self.action_type = "edit"
        self.accept()

    def on_new_clicked(self):
        self.action_type = "new"
        self.accept()

class MedicationManagementPage(QWidget):
    """
    Modern Restock Controller incorporating Partner's QSpinBox and QDateEdit controls
    with Smart Fill, Focus Highlights, and Integrated Touch Virtual Keyboard.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.current_user_record_id = None
        self.current_focused_input = None
        self.existing_record_id = None

        self.internal_stack = QStackedWidget(self)

        self.init_scan_page()  # Index 0
        self.init_form_page()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

    def set_current_user(self, user_record_id):
        self.current_user_record_id = user_record_id

    # =====================================================================
    # 🎴 SCREEN 0: Initial Barcode Scan
    # =====================================================================
    def init_scan_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel("📦 Stock Ingestion Engine")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A; border: none;")

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "padding: 6px 14px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; color: #475569; border: 1px solid #E2E8F0;")
        back_btn.clicked.connect(self.clear_all_fields)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        left_layout.addSpacing(20)
        left_layout.addWidget(QLabel("Scan Product Barcode Identity:"))
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode or enter manually...")
        self.barcode_input.setStyleSheet(
            "padding: 14px; border: 2px solid #CBD5E1; border-radius: 10px; font-size: 14px;")
        self.barcode_input.focusInEvent = lambda event: self.handle_input_focus(self.barcode_input, event)
        self.barcode_input.returnPressed.connect(self.check_barcode)
        left_layout.addWidget(self.barcode_input)

        search_btn = QPushButton("🔍 Verify Cloud & Smart Fill")
        search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        search_btn.setStyleSheet(
            "background-color: #0D9488; color: white; padding: 14px; font-weight: bold; border-radius: 10px; border: none; font-size: 14px;")
        search_btn.clicked.connect(self.check_barcode)
        left_layout.addWidget(search_btn)
        left_layout.addStretch()

        main_layout.addWidget(left_card, stretch=4)

        kb_card = QFrame()
        kb_card.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(kb_card)
        kb_layout.addWidget(QLabel("Numeric Entry Pad:"))

        num_grid = QVBoxLayout()
        num_grid.setSpacing(6)
        rows = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['Clear', '0', '⌫']]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(6)
            for k in row:
                btn = QPushButton(k)
                btn.setFocusPolicy(Qt.NoFocus)
                if k in ['Clear', '⌫']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 16px 0; border-radius: 8px; border: none;")
                else:
                    btn.setStyleSheet(
                        "background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 16px 0; border-radius: 8px; border: 1px solid #E2E8F0;")
                btn.clicked.connect(lambda checked, key=k: self.handle_key_press(key))
                r_lay.addWidget(btn)
            num_grid.addLayout(r_lay)
        kb_layout.addLayout(num_grid)
        kb_layout.addStretch()

        main_layout.addWidget(kb_card, stretch=5)
        self.internal_stack.addWidget(page)

    # =====================================================================
    # 📝 SCREEN 1: Data Entry Form (دمج الـ QSpinBox والـ QDateEdit المضيء)
    # =====================================================================
    def init_form_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        form_card = QFrame()
        form_card.setStyleSheet("""
            background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;
            QDateEdit, QSpinBox {
                padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; 
                font-size: 13px; background-color: #F8FAFC; color: #0F172A;
            }
        """)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(5)

        self.form_title = QLabel("Register New Medication Stock")
        self.form_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0D9488; margin-bottom: 5px;")
        form_layout.addWidget(self.form_title)

        form_layout.addWidget(QLabel("Medicine Name"))
        self.name_input = QLineEdit()
        self.name_input.focusInEvent = lambda event: self.handle_input_focus(self.name_input, event)
        form_layout.addWidget(self.name_input)

        form_layout.addWidget(QLabel("Active Pharmaceutical Ingredient"))
        self.ingredient_input = QLineEdit()
        self.ingredient_input.focusInEvent = lambda event: self.handle_input_focus(self.ingredient_input, event)
        form_layout.addWidget(self.ingredient_input)

        form_layout.addWidget(QLabel("Dosage Strength (mg/ml)"))
        self.dosage_input = QLineEdit()
        self.dosage_input.focusInEvent = lambda event: self.handle_input_focus(self.dosage_input, event)
        form_layout.addWidget(self.dosage_input)

        form_layout.addWidget(QLabel("Batch Number / Serial"))
        self.batch_input = QLineEdit()
        self.batch_input.focusInEvent = lambda event: self.handle_input_focus(self.batch_input, event)
        form_layout.addWidget(self.batch_input)

        # 📅 فكرة شريكتك: حقل تاريخ منبثق ذكي ومضمون التنسيق
        form_layout.addWidget(QLabel("Product Expiry Date"))
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate())
        self.expiry_input.focusInEvent = lambda event: self.handle_input_focus(self.expiry_input, event)
        form_layout.addWidget(self.expiry_input)

        # 🔢 فكرة شريكتك: سبين بوكس يمنع السوالب والأصفار برمجياً ومطلقاً!
        form_layout.addWidget(QLabel("Pills Count (Quantity)"))
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 5000)  # نطاق أمان صارم يبدأ من 1 حبة فما فوق
        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event)
        form_layout.addWidget(self.quantity_input)

        self.submit_med_btn = QPushButton("💾 Commit New Stock to Cloud")
        self.submit_med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_med_btn.setStyleSheet(
            "background-color: #0D9488; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none; font-size: 14px; margin-top: 5px;")
        self.submit_med_btn.clicked.connect(self.save_medication)
        form_layout.addWidget(self.submit_med_btn)

        cancel_btn = QPushButton("❌ Cancel & Go Back")
        cancel_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 8px; font-weight: 600; border-radius: 8px; border: 1px solid #E2E8F0;")
        cancel_btn.clicked.connect(lambda: self.internal_stack.setCurrentIndex(0))
        form_layout.addWidget(cancel_btn)

        main_layout.addWidget(form_card, stretch=4)

        # ⌨️ الكيبورد الكامل للـ Form ليدعم اللمس والفوكس المضيء للـ LineEdits والـ SpinBox
        kb_full_card = QFrame()
        kb_full_card.setStyleSheet("background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;")
        kb_full_layout = QVBoxLayout(kb_full_card)
        kb_full_layout.addWidget(QLabel("Form Touch Input Workspace:"))

        keyboard_widget = QWidget()
        keyboard_lay = QVBoxLayout(keyboard_widget)
        keyboard_lay.setContentsMargins(0, 0, 0, 0)
        keyboard_lay.setSpacing(4)
        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', '⌫']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(
                    "background-color: #F1F5F9; color: #1E293B; font-weight: 600; padding: 12px 4px; border-radius: 6px; border: 1px solid #E2E8F0;")
                if key in ['Clear', '⌫']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; padding: 12px 4px; border-radius: 6px; border: none;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #F1F5F9; color: #1E293B; font-weight: bold; padding: 12px 4px; border-radius: 6px; min-width: 55px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            keyboard_lay.addLayout(r_lay)
        kb_full_layout.addWidget(keyboard_widget)
        kb_full_layout.addStretch()

        main_layout.addWidget(kb_full_card, stretch=5)
        self.internal_stack.addWidget(page)

    # =====================================================================
    # ⚙️ LOGIC & LOGISTICS CONTROLS
    # =====================================================================
    def handle_input_focus(self, input_field, event):
        # تصفير ستايلات كل الحقول لتبدو افتراضية ونظيفة
        for box in [self.barcode_input, self.name_input, self.ingredient_input, self.dosage_input, self.batch_input]:
            box.setStyleSheet(
                "padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 13px; background-color: #F8FAFC;")
        self.expiry_input.setStyleSheet(
            "padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 13px; background-color: #F8FAFC; color: #0F172A;")
        self.quantity_input.setStyleSheet(
            "padding: 10px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 13px; background-color: #F8FAFC; color: #0F172A;")

        self.current_focused_input = input_field

        # استدعاء الفوكس الطبيعي حسب نوع الكنترول
        if event:
            if isinstance(input_field, QLineEdit):
                super(QLineEdit, input_field).focusInEvent(event)
            elif isinstance(input_field, QSpinBox):
                super(QSpinBox, input_field).focusInEvent(event)
            elif isinstance(input_field, QDateEdit):
                super(QDateEdit, input_field).focusInEvent(event)

        # إضاءة الحقل المختار حالياً باللون الفيروزي المضيء بشكل موحد وفخم!
        input_field.setStyleSheet(
            "padding: 10px; border: 2px solid #0D9488; border-radius: 8px; font-size: 13px; background-color: #F0FDFA; color: #0F172A; font-weight: bold;")

    def handle_key_press(self, key):
        if not self.current_focused_input: return

        # التحكم بالـ QSpinBox عبر الكيبورد الوهمي باللمس
        if isinstance(self.current_focused_input, QSpinBox):
            current_val = str(self.current_focused_input.value())
            if key == '⌫':
                new_val = current_val[:-1]
                self.current_focused_input.setValue(int(new_val) if new_val and new_val != '-' else 1)
            elif key == 'Clear':
                self.current_focused_input.setValue(1)
            elif key.isdigit():
                # دمج الرقم الجديد مع القيمة الحالية للـ SpinBox
                if current_val == "1" and key != "0":  # استبدال الرقم الابتدائي الافتراضي
                    self.current_focused_input.setValue(int(key))
                else:
                    self.current_focused_input.setValue(int(current_val + key))

        # التحكم بالـ QLineEdit العادي
        elif isinstance(self.current_focused_input, QLineEdit):
            current_text = self.current_focused_input.text()
            if key == '⌫':
                self.current_focused_input.setText(current_text[:-1])
            elif key == 'Clear':
                self.current_focused_input.clear()
            else:
                self.current_focused_input.setText(current_text + key)

        self.current_focused_input.setFocus(Qt.OtherFocusReason)

    def check_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            QMessageBox.warning(self, "Error", "Please enter or scan a barcode.")
            return

        try:
            existing_batches = airtable_api.find_all_batches_by_barcode(barcode)

            if existing_batches:
                from screen.stock_page import BatchSelectionDialog
                from PyQt5.QtWidgets import QDialog

                dialog = BatchSelectionDialog(existing_batches, self)
                if dialog.exec_() == QDialog.Accepted:
                    if dialog.action_type == "edit":
                        selected = dialog.selected_batch
                        self.existing_record_id = selected["id"]

                        record = airtable_api.stock_table.get(self.existing_record_id)
                        fields = record.get('fields', {})

                        self.name_input.setText(str(fields.get("Medicine Name", "")))
                        self.name_input.setEnabled(True)
                        self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                        self.ingredient_input.setEnabled(True)
                        self.dosage_input.setText(str(fields.get("Dosage", "")))
                        self.dosage_input.setEnabled(True)

                        self.batch_input.setText(str(selected["batch_number"]))

                        # تحويل صيغة تاريخ Airtable المرتجع الكترونياً ليعبئ الـ QDateEdit تلقائياً بذكاء
                        qdate_obj = QDate.fromString(selected["expiry_date"], "yyyy-MM-dd")
                        self.expiry_input.setDate(qdate_obj)
                        self.quantity_input.setValue(int(selected["current_quantity"]))

                        self.form_title.setText("📝 Edit/Correct Batch Details")
                        self.submit_med_btn.setText("🆙 Update Existing Batch Record")
                        self.submit_med_btn.setStyleSheet(
                            "background-color: #2563EB; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none;")
                        self.internal_stack.setCurrentIndex(1)
                        self.handle_input_focus(self.quantity_input, None)

                    elif dialog.action_type == "new":
                        self.existing_record_id = None
                        first_batch = existing_batches[0]

                        self.name_input.setText(first_batch["medicine_name"])
                        self.name_input.setEnabled(False)

                        record = airtable_api.stock_table.get(first_batch["id"])
                        fields = record.get('fields', {})
                        self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                        self.ingredient_input.setEnabled(False)
                        self.dosage_input.setText(str(fields.get("Dosage", "")))
                        self.dosage_input.setEnabled(False)

                        self.batch_input.clear()
                        self.expiry_input.setDate(QDate.currentDate())
                        self.quantity_input.setValue(1)

                        self.form_title.setText("➕ Register New Product Batch (Smart Fill)")
                        self.submit_med_btn.setText("💾 Commit New Stock to Cloud")
                        self.submit_med_btn.setStyleSheet(
                            "background-color: #0D9488; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none;")

                        self.internal_stack.setCurrentIndex(1)
                        self.handle_input_focus(self.batch_input, None)
            else:
                self.existing_record_id = None
                self.name_input.clear()
                self.name_input.setEnabled(True)
                self.ingredient_input.clear()
                self.ingredient_input.setEnabled(True)
                self.dosage_input.clear()
                self.dosage_input.setEnabled(True)
                self.batch_input.clear()
                self.expiry_input.setDate(QDate.currentDate())
                self.quantity_input.setValue(1)

                self.form_title.setText("✨ Ingest Brand New Medicine Type")
                self.submit_med_btn.setText("💾 Commit New Stock to Cloud")
                self.submit_med_btn.setStyleSheet(
                    "background-color: #0D9488; color: white; padding: 12px; font-weight: bold; border-radius: 8px; border: none;")

                self.internal_stack.setCurrentIndex(1)
                self.handle_input_focus(self.name_input, None)

        except Exception as e:
            print(f"Error during check barcode: {e}")

    def save_medication(self):
        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()
        ingredient = self.ingredient_input.text().strip()
        dosage = self.dosage_input.text().strip()
        batch = self.batch_input.text().strip()

        # استخراج التاريخ بصيغة آمنة وموحدة ومقبولة عالمياً لدى قواعد البيانات البرمجية
        clean_expiry_str = self.expiry_input.date().toString("yyyy-MM-dd")
        qty = self.quantity_input.value()  # يجلب القيمة كرقم مباشر جاهز ومحمي ضد السوالب والأصفار!

        if not barcode or not name or not batch:
            QMessageBox.warning(self, "Input Error ⚠️",
                                "Barcode, Medicine Name, and Batch Number are mandatory fields.")
            return

        # فحص جودة وصحة التاريخ برمجياً لضمان عدم إدخال أدوية منتهية الصلاحية مسبقاً
        selected_date = datetime.strptime(clean_expiry_str, "%Y-%m-%d").date()
        if selected_date < datetime.now().date():
            QMessageBox.critical(self, "Expired Medication ❌",
                                 "Cannot ingest stock that is already expired or ends today.")
            return

        try:
            if self.existing_record_id:
                record = airtable_api.update_medication_full_fields(self.existing_record_id, name, barcode, ingredient,
                                                                    dosage, clean_expiry_str, qty, batch)
                if record:
                    QMessageBox.information(self, "Updated ✅", f"Batch record for '{name}' overwritten successfully!")
                    self.clear_all_fields()
            else:
                record = airtable_api.add_new_medication(
                    name, barcode, ingredient, dosage, clean_expiry_str, qty, qty, batch,
                    user_record_id=self.current_user_record_id
                )
                if record:
                    QMessageBox.information(self, "Success ✅", f"Stock batch for '{name}' synced to cloud repository!")
                    self.clear_all_fields()
        except Exception as e:
            QMessageBox.critical(self, "Server Error ❌", f"Sync process failed:\n{str(e)}")

    def clear_all_fields(self):
        self.barcode_input.clear()
        self.name_input.clear()
        self.ingredient_input.clear()
        self.dosage_input.clear()
        self.batch_input.clear()
        self.expiry_input.setDate(QDate.currentDate())
        self.quantity_input.setValue(1)
        self.existing_record_id = None
        self.internal_stack.setCurrentIndex(0)
        self.handle_input_focus(self.barcode_input, None)