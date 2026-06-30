import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QFrame, QMessageBox, QHeaderView, QStackedWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
import airtable_api


class StaffFormPage(QWidget):
    """ واجهة إدخال وتعديل بيانات الموظفين ممتدة بالكامل (Full Screen) ومصممة خصيصاً لشاشات الرازبري العريضة """

    def __init__(self, parent=None, on_close_callback=None):
        super().__init__(parent)
        self.on_close_callback = on_close_callback
        self.user_data = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # =====================================================================
        # 📋 القسم الأيسر: استمارة البيانات والأزرار (50% من الشاشة)
        # =====================================================================
        form_card = QFrame()
        form_card.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }
            QLabel { font-size: 14px; font-weight: 600; color: #475569; border: none; }
            QLineEdit { padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; background-color: #F8FAFC; color: #1E293B; }
            QComboBox { padding: 8px; border: 1px solid #E2E8F0; border-radius: 6px; background-color: #FFFFFF; font-size: 14px; }
        """)

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(6)

        self.form_title = QLabel("➕ Register New Staff Member")
        self.form_title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #6366F1; margin-bottom: 4px; border: none;")
        form_layout.addWidget(self.form_title)

        form_layout.addWidget(QLabel("Full Name"))
        self.fullname_input = QLineEdit()
        self.fullname_input.focusInEvent = lambda event: self.handle_input_focus(self.fullname_input, event)
        form_layout.addWidget(self.fullname_input)

        form_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.focusInEvent = lambda event: self.handle_input_focus(self.username_input, event)
        form_layout.addWidget(self.username_input)

        form_layout.addWidget(QLabel("Password / Key"))
        self.password_input = QLineEdit()
        self.password_input.focusInEvent = lambda event: self.handle_input_focus(self.password_input, event)
        form_layout.addWidget(self.password_input)

        form_layout.addWidget(QLabel("System PIN"))
        self.pincode_input = QLineEdit()
        self.pincode_input.focusInEvent = lambda event: self.handle_input_focus(self.pincode_input, event)
        form_layout.addWidget(self.pincode_input)

        form_layout.addWidget(QLabel("Privilege Level"))
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["Maneger", "Doctor", "Nurse", "Assistant"])
        self.role_combobox.currentIndexChanged.connect(self.toggle_email_field_visibility)
        form_layout.addWidget(self.role_combobox)

        self.email_container = QWidget()
        self.email_container.setStyleSheet("border: none; background: transparent;")
        email_lay = QVBoxLayout(self.email_container)
        email_lay.setContentsMargins(0, 0, 0, 0)
        email_lay.setSpacing(4)
        email_lay.addWidget(QLabel("Manager Email Address (For Expiry Alerts)"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("manager@clinic.com")
        self.email_input.focusInEvent = lambda event: self.handle_input_focus(self.email_input, event)
        email_lay.addWidget(self.email_input)
        form_layout.addWidget(self.email_container)

        form_layout.addStretch()

        btn_layout = QHBoxLayout()
        self.back_btn = QPushButton("⬅️ Back")
        self.back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.back_btn.setStyleSheet(
            "background-color: #64748B; color: white; padding: 12px; font-weight: bold; border-radius: 6px; font-size: 14px; border: none;")
        self.back_btn.clicked.connect(self.handle_back_click)

        self.submit_btn = QPushButton("💾 Save Account")
        self.submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 12px; font-weight: bold; border-radius: 6px; font-size: 14px; border: none;")
        self.submit_btn.clicked.connect(self.handle_save)

        btn_layout.addWidget(self.back_btn, stretch=1)
        btn_layout.addWidget(self.submit_btn, stretch=2)
        form_layout.addLayout(btn_layout)

        main_layout.addWidget(form_card, stretch=4)

        # =====================================================================
        # ⌨️ القسم الأيمن: التاتش باد الموسع بالكامل العريض (50% من الشاشة)
        # =====================================================================
        kb_card = QFrame()
        kb_card.setStyleSheet("""
            QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; }
            QPushButton { 
                background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 15px; 
                border: 1px solid #CBD5E1; border-radius: 6px; 
            }
            QPushButton:pressed { background-color: #E2E8F0; }
        """)
        kb_layout = QVBoxLayout(kb_card)
        kb_layout.setContentsMargins(10, 10, 10, 10)
        kb_layout.setSpacing(5)

        title_kb = QLabel("⌨️ Touch Workspace Keyboard")
        title_kb.setStyleSheet("font-size: 13px; color: #64748B; font-weight: bold; border: none; margin-bottom: 2px;")
        kb_layout.addWidget(title_kb)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', '@', '.', '⌫'],
            ['Space', 'Clear']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(45)

                if key in ['⌫', 'Clear']:
                    btn.setStyleSheet("background-color: #CBD5E1; color: #1E293B; border: none; min-width: 55px; padding: 8px 0px; font-size: 14px;")
                elif key == 'Space':
                    btn.setStyleSheet("background-color: #FFFFFF; min-width: 180px; padding: 8px 0px; font-size: 14px;")
                else:
                    btn.setStyleSheet("background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 15px; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 0px;")

                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            kb_layout.addLayout(row_layout)

        main_layout.addWidget(kb_card, stretch=5)

        self.toggle_email_field_visibility()
        self.handle_input_focus(self.fullname_input, None)

    def set_user_data(self, user_data=None):
        self.user_data = user_data
        if user_data:
            self.form_title.setText("📝 Edit Staff Member Account")
            self.fullname_input.setText(str(user_data.get("Full Name", "")))
            self.username_input.setText(str(user_data.get("Username", "")))
            self.password_input.setText(str(user_data.get("Password", "")))
            pin_raw = str(user_data.get("PIN Code", ""))
            self.pincode_input.setText(pin_raw.split(".")[0] if "." in pin_raw else pin_raw)
            self.email_input.setText(str(user_data.get("Email", "")))
            idx = self.role_combobox.findText(str(user_data.get("Role", "Assistant")))
            if idx >= 0: self.role_combobox.setCurrentIndex(idx)
        else:
            self.form_title.setText("➕ Register New Staff Member")
            self.fullname_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.pincode_input.clear()
            self.email_input.clear()
            self.role_combobox.setCurrentIndex(0)

        self.toggle_email_field_visibility()
        self.handle_input_focus(self.fullname_input, None)

    def toggle_email_field_visibility(self):
        if self.role_combobox.currentText() == "Maneger":
            self.email_container.show()
        else:
            self.email_input.clear()
            self.email_container.hide()

    def handle_input_focus(self, input_field, event):
        for box in [self.fullname_input, self.username_input, self.password_input, self.pincode_input, self.email_input]:
            box.setStyleSheet(
                "padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; background-color: #F8FAFC; color: #1E293B;")
        self.current_focused_input = input_field
        if event: super(QLineEdit, input_field).focusInEvent(event)
        input_field.setStyleSheet(
            "padding: 8px; border: 2px solid #6366F1; border-radius: 6px; font-size: 14px; background-color: #F5F3FF; color: #0F172A;")

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        txt = self.current_focused_input.text()
        if key == '⌫':
            self.current_focused_input.setText(txt[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        elif key == 'Space':
            self.current_focused_input.setText(txt + ' ')
        else:
            self.current_focused_input.setText(txt + key)

    def handle_back_click(self):
        if self.on_close_callback: self.on_close_callback(False)

    def handle_save(self):
        fn = self.fullname_input.text().strip()
        un = self.username_input.text().strip()
        ps = self.password_input.text().strip()
        pin = self.pincode_input.text().strip()
        role = self.role_combobox.currentText()
        email = self.email_input.text().strip()

        if not fn or not un or not ps or not pin:
            QMessageBox.warning(self, "Validation Error ⚠️", "All general fields are mandatory.")
            return

        if role == "Maneger" and not email:
            QMessageBox.critical(self, "Email Required 📧", "Security Alert: Managers MUST provide an email for alerts!")
            return

        try:
            if self.user_data:
                airtable_api.update_user_records(self.user_data.get("record_id"), un, ps, role, pin, fn)
                airtable_api.users_table.update(self.user_data.get("record_id"),
                                                {"Email": email if role == "Maneger" else ""})
            else:
                user_payload = {
                    "Username": str(un), "Password": str(ps), "Role": str(role), "PIN Code": str(pin),
                    "Full Name": str(fn), "Email": str(email) if role == "Maneger" else ""
                }
                airtable_api.users_table.create(user_payload, typecast=True)

            if self.on_close_callback: self.on_close_callback(True)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))


class UserManagementPage(QWidget):
    """ الواجهة الرئيسية المحدثة المكونة من قطاع الـ Stack للتنقل الكامل بين الجداول والاستمارة """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.init_ui()

    def init_ui(self):
        self.outer_stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.outer_stack)

        # ----------------------------------------------------
        # الصفحة 0: جدول الحسابات الرئيسي (العرض الكامل)
        # ----------------------------------------------------
        self.main_view_widget = QWidget()
        view_layout = QVBoxLayout(self.main_view_widget)
        view_layout.setContentsMargins(5, 5, 5, 5)
        view_layout.setSpacing(6)

        container = QFrame()
        container.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(8)

        navigation_tabs = QHBoxLayout()
        self.tab_users_btn = QPushButton("👥 Staff Accounts")
        self.tab_users_btn.setCheckable(True)
        self.tab_users_btn.setChecked(True)
        self.tab_users_btn.setStyleSheet(self.get_tab_style(active=True))
        self.tab_users_btn.clicked.connect(lambda: self.switch_admin_tab(0))

        self.tab_meds_btn = QPushButton("🗑️ Disposal Inventory")
        self.tab_meds_btn.setCheckable(True)
        self.tab_meds_btn.setStyleSheet(self.get_tab_style(active=False))
        self.tab_meds_btn.clicked.connect(lambda: self.switch_admin_tab(1))

        self.add_staff_fab = QPushButton("➕ Add New Staff")
        self.add_staff_fab.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px; font-size: 13px; border: none;")
        self.add_staff_fab.clicked.connect(self.navigate_to_add_form)

        back_btn = QPushButton("⬅️ Menu")
        back_btn.setStyleSheet(
            "padding: 6px 14px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; border: 1px solid #E2E8F0; color: #475569; font-size: 13px;")
        back_btn.clicked.connect(self.on_back_to_menu)

        navigation_tabs.addWidget(self.tab_users_btn)
        navigation_tabs.addWidget(self.tab_meds_btn)
        navigation_tabs.addWidget(self.add_staff_fab)
        navigation_tabs.addStretch()
        navigation_tabs.addWidget(back_btn)
        container_layout.addLayout(navigation_tabs)

        self.admin_sub_stack = QStackedWidget()

        self.page_users_widget = QTableWidget()
        self.page_users_widget.setColumnCount(4)
        self.page_users_widget.setHorizontalHeaderLabels(["Username", "Role", "Email Contact", "Actions"])
        self.page_users_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.page_users_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.page_users_widget.setStyleSheet(self.get_table_style())

        header = self.page_users_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.page_users_widget.setColumnWidth(3, 100)
        self.page_users_widget.verticalHeader().setDefaultSectionSize(36)
        self.admin_sub_stack.addWidget(self.page_users_widget)

        self.page_meds_list = QListWidget()
        self.page_meds_list.setStyleSheet(
            "border: 1px solid #E2E8F0; border-radius: 6px; background: #F8FAFC; font-size: 14px;")
        self.admin_sub_stack.addWidget(self.page_meds_list)

        container_layout.addWidget(self.admin_sub_stack)

        self.refresh_hub_btn = QPushButton("🔄 Sync Cloud Directory")
        self.refresh_hub_btn.setStyleSheet(
            "padding: 10px; font-size: 13px; font-weight: bold; background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; color: #475569;")
        self.refresh_hub_btn.clicked.connect(self.sync_current_hub_view)
        container_layout.addWidget(self.refresh_hub_btn)
        view_layout.addWidget(container)

        self.outer_stack.addWidget(self.main_view_widget)

        # ----------------------------------------------------
        # الصفحة 1: صفحة الاستمارة الكاملة (Full Screen Form)
        # ----------------------------------------------------
        self.form_page_widget = StaffFormPage(self, on_close_callback=self.handle_form_callback)
        self.outer_stack.addWidget(self.form_page_widget)

        self.switch_admin_tab(0)

    def navigate_to_add_form(self):
        self.form_page_widget.set_user_data(None)
        self.outer_stack.setCurrentIndex(1)

    def navigate_to_edit_form(self, user_data):
        self.form_page_widget.set_user_data(user_data)
        self.outer_stack.setCurrentIndex(1)

    def handle_form_callback(self, is_saved):
        self.outer_stack.setCurrentIndex(0)
        if is_saved:
            QMessageBox.information(self, "Success ✅", "Database synchronized successfully.")
            self.load_users_data()

    def switch_admin_tab(self, index):
        self.admin_sub_stack.setCurrentIndex(index)
        if index == 0:
            self.tab_users_btn.setChecked(True)
            self.tab_users_btn.setStyleSheet(self.get_tab_style(active=True))
            self.tab_meds_btn.setChecked(False)
            self.tab_meds_btn.setStyleSheet(self.get_tab_style(active=False))
            self.add_staff_fab.show()
            self.load_users_data()
        else:
            self.tab_users_btn.setChecked(False)
            self.tab_users_btn.setStyleSheet(self.get_tab_style(active=False))
            self.tab_meds_btn.setChecked(True)
            self.tab_meds_btn.setStyleSheet(self.get_tab_style(active=True))
            self.add_staff_fab.hide()
            self.load_inventory_disposal_data()

    def sync_current_hub_view(self):
        if self.admin_sub_stack.currentIndex() == 0:
            self.load_users_data()
        else:
            self.load_inventory_disposal_data()

    def load_users_data(self):
        try:
            users = airtable_api.get_all_users()
            self.page_users_widget.setRowCount(0)
            for row_idx, user_data in enumerate(users):
                self.page_users_widget.insertRow(row_idx)
                role_val = user_data.get("Role", "N/A")
                if isinstance(role_val, list): role_val = role_val[0] if role_val else "N/A"
                email_val = user_data.get("Email", "-") if role_val == "Maneger" else "-"

                u_item = QTableWidgetItem(str(user_data.get("Username", "N/A")))
                r_item = QTableWidgetItem(str(role_val))
                e_item = QTableWidgetItem(str(email_val))

                u_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                r_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                e_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                self.page_users_widget.setItem(row_idx, 0, u_item)
                self.page_users_widget.setItem(row_idx, 1, r_item)
                self.page_users_widget.setItem(row_idx, 2, e_item)

                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(6)

                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(32, 32)
                edit_btn.setStyleSheet(
                    "background-color: #0EA5E9; color: white; border-radius: 6px; border: none; font-size: 14px;")
                edit_btn.clicked.connect(lambda checked, u=user_data: self.navigate_to_edit_form(u))

                del_btn = QPushButton("🗑️")
                del_btn.setFixedSize(32, 32)
                del_btn.setStyleSheet(
                    "background-color: #EF4444; color: white; border-radius: 6px; border: none; font-size: 14px;")
                del_btn.clicked.connect(lambda checked, u=user_data: self.handle_delete_user(u))

                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(del_btn)
                actions_layout.addStretch()
                self.page_users_widget.setCellWidget(row_idx, 3, actions_widget)
        except Exception as e:
            print(f"Error table sync: {e}")

    def handle_delete_user(self, user_data):
        username = user_data.get("Username", "Unknown")
        confirm = QMessageBox.question(self, "Delete Staff Account ⚠️",
                                       f"Are you sure you want to permanently delete staff account '{username}'?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                if airtable_api.delete_user_record(user_data.get("record_id")):
                    QMessageBox.information(self, "Deleted 🗑️", f"Account '{username}' removed completely.")
                    self.load_users_data()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", str(e))

    def load_inventory_disposal_data(self):
        self.page_meds_list.clear()
        try:
            if not hasattr(airtable_api, 'stock_table') or airtable_api.stock_table is None: return
            records = airtable_api.stock_table.all()

            cached_meds = []
            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                qty = int(fields.get("Current Pills Count", 0))
                if qty > 0:
                    cached_meds.append({
                        "id": r.id if hasattr(r, 'id') else r.get('id'),
                        "name": fields.get("Medicine Name", "Unknown"),
                        "barcode": fields.get("Barcode", ""),
                        "batch": fields.get("A Batch", "N/A"),
                        "expiry": fields.get("Expiry Date", "9999-12-31"),
                        "qty": qty
                    })
            cached_meds.sort(key=lambda x: x['expiry'])

            for med in cached_meds:
                display_text = f"📅 [{med['expiry']}] | 💊 {med['name']} | Batch: {med['batch']} | Qty: {med['qty']}"
                item = QListWidgetItem()
                self.page_meds_list.addItem(item)

                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(12, 6, 12, 6)

                info_label = QLabel(display_text)
                info_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
                row_layout.addWidget(info_label)
                row_layout.addStretch()

                purge_btn = QPushButton("🗑️ Purge Record")
                purge_btn.setFixedSize(130, 34)
                purge_btn.setStyleSheet(
                    "background-color: #EF4444; color: white; border-radius: 6px; font-weight: bold; font-size: 13px; border: none;")
                purge_btn.clicked.connect(lambda checked, m=med: self.execute_emergency_medicine_purge(m))

                row_layout.addWidget(purge_btn)
                row_widget.setLayout(row_layout)
                item.setSizeHint(row_widget.sizeHint())
                self.page_meds_list.setItemWidget(item, row_widget)
        except Exception as e:
            print(f"Error inventory sync: {e}")

    def execute_emergency_medicine_purge(self, med_data):
        confirm = QMessageBox.critical(self, "Emergency Purge ⚠️",
                                       f"Are you sure you want to permanently delete batch '{med_data['batch']}' for '{med_data['name']}'?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                if airtable_api.delete_medication_record(med_data["id"]):
                    airtable_api.log_transaction("ADMIN_PURGE_DELETE", med_data["barcode"], "System Manager",
                                                 med_data["qty"], "Manager Portal Emergency Disposal")
                    QMessageBox.information(self, "Purged ✅", "Batch deleted successfully.")
                    self.load_inventory_disposal_data()
            except Exception as e:
                QMessageBox.critical(self, "Server Error ❌", str(e))

    def get_tab_style(self, active=True):
        if active: return "background-color: #6366F1; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px; font-size: 13px; border: none;"
        return "background-color: #F1F5F9; color: #475569; font-weight: bold; padding: 8px 16px; border-radius: 6px; font-size: 13px; border: 1px solid #E2E8F0;"

    def get_table_style(self):
        return """
            QTableWidget { background-color: #FFFFFF; color: #334155; font-size: 14px; border: none; }
            QHeaderView::section { background-color: #F8FAFC; font-weight: bold; border: none; padding: 8px; color: #64748B; font-size: 14px; border-bottom: 2px solid #E2E8F0; }
            QTableWidget::item { padding: 6px; border-bottom: 1px solid #F1F5F9; }
            QTableWidget::item:selected { background-color: #EEF2FF; color: #4F46E5; }
        """