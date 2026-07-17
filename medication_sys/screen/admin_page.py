import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QFrame, QMessageBox, QHeaderView, QStackedWidget,
    QScrollArea, QSizePolicy, QDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor


def make_dialog_kiosk_safe(dialog):
    flags = dialog.windowFlags()
    flags |= Qt.Dialog
    flags |= Qt.WindowStaysOnTopHint
    flags &= ~Qt.WindowMinimizeButtonHint
    flags &= ~Qt.WindowMaximizeButtonHint
    dialog.setWindowFlags(flags)
    dialog.setWindowModality(Qt.ApplicationModal)


def keep_dialog_visible(dialog):
    try:
        dialog.showNormal()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        pass


def show_safe_message(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    make_dialog_kiosk_safe(box)
    QTimer.singleShot(0, lambda: keep_dialog_visible(box))
    return box.exec_()


def ask_safe_confirmation(parent, icon, title, text):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    make_dialog_kiosk_safe(box)
    QTimer.singleShot(0, lambda: keep_dialog_visible(box))
    return box.exec_() == QMessageBox.Yes


def make_scroll_area(widget):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    scroll.setStyleSheet("""
        QScrollArea { border: none; background-color: transparent; }
        QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; }
        QScrollBar::handle:vertical { background: #CBD5E1; min-height: 35px; border-radius: 7px; }
        QScrollBar:horizontal { border: none; background: #F1F5F9; height: 14px; margin: 0px; border-radius: 7px; }
        QScrollBar::handle:horizontal { background: #CBD5E1; min-width: 35px; border-radius: 7px; }
    """)
    scroll.setWidget(widget)
    return scroll


class StaffFormPage(QWidget):
    """ Full-screen layout workspace dedicated to inputting or updating staff member data. """

    def __init__(self, parent=None, on_close_callback=None):
        super().__init__(parent)
        self.on_close_callback = on_close_callback
        self.user_data = None
        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        page_content = QWidget()
        page_content.setStyleSheet("background-color: #F8FAFC;")
        page_content.setMinimumHeight(560)

        main_layout = QHBoxLayout(page_content)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        form_card = QFrame()
        form_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        form_card.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }
            QLabel { font-size: 13px; font-weight: bold; color: #475569; border: none; }
            QLineEdit { padding: 7px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; background-color: #F8FAFC; color: #1E293B; }
            QLineEdit:focus { border: 2px solid #6366F1; background-color: #F5F3FF; }
            QComboBox { padding: 7px; border: 1px solid #E2E8F0; border-radius: 6px; background-color: #FFFFFF; font-size: 13px; color: #1E293B; }
            QComboBox:focus { border: 2px solid #6366F1; }
        """)

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(7)

        self.form_title = QLabel("Register New Staff Member")
        self.form_title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #6366F1; margin-bottom: 8px; border: none;")
        form_layout.addWidget(self.form_title)

        form_layout.addWidget(QLabel("Full Name"))
        self.fullname_input = QLineEdit()
        form_layout.addWidget(self.fullname_input)

        form_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        form_layout.addWidget(self.username_input)

        form_layout.addWidget(QLabel("Password / Key"))
        self.password_input = QLineEdit()
        form_layout.addWidget(self.password_input)

        form_layout.addWidget(QLabel("System PIN"))
        self.pincode_input = QLineEdit()
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
        email_lay.setSpacing(6)
        email_lay.addWidget(QLabel("Manager Email Address (For Expiry Alerts)"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("manager@clinic.com")
        email_lay.addWidget(self.email_input)
        form_layout.addWidget(self.email_container)

        form_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.back_btn = QPushButton("Back")
        self.back_btn.setMinimumHeight(38)
        self.back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.back_btn.setStyleSheet(
            "background-color: #64748B; color: white; padding: 12px; font-weight: bold; border-radius: 8px; font-size: 16px; border: none;")
        self.back_btn.clicked.connect(self.handle_back_click)

        self.submit_btn = QPushButton("Save Account")
        self.submit_btn.setMinimumHeight(38)
        self.submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_btn.setStyleSheet(
            "background-color: #10B981; color: white; padding: 12px; font-weight: bold; border-radius: 8px; font-size: 16px; border: none;")
        self.submit_btn.clicked.connect(self.handle_save)

        btn_layout.addWidget(self.back_btn, stretch=1)
        btn_layout.addWidget(self.submit_btn, stretch=2)
        form_layout.addLayout(btn_layout)

        main_layout.addWidget(form_card)

        page_scroll = make_scroll_area(page_content)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        outer_layout.addWidget(page_scroll)

        self.toggle_email_field_visibility()
        self.fullname_input.setFocus()

    def set_user_data(self, user_data=None):
        self.user_data = user_data
        if user_data:
            self.form_title.setText("Edit Staff Member Account")
            self.fullname_input.setText(str(user_data.get("Full Name", "")))
            self.username_input.setText(str(user_data.get("Username", "")))
            self.password_input.setText(str(user_data.get("Password", "")))
            pin_raw = str(user_data.get("PIN Code", ""))
            self.pincode_input.setText(pin_raw.split(".")[0] if "." in pin_raw else pin_raw)
            self.email_input.setText(str(user_data.get("Email", "")))
            idx = self.role_combobox.findText(str(user_data.get("Role", "Assistant")))
            if idx >= 0: self.role_combobox.setCurrentIndex(idx)
        else:
            self.form_title.setText("Register New Staff Member")
            self.fullname_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.pincode_input.clear()
            self.email_input.clear()
            self.role_combobox.setCurrentIndex(0)

        self.toggle_email_field_visibility()
        self.fullname_input.setFocus()

    def toggle_email_field_visibility(self):
        if self.role_combobox.currentText() == "Maneger":
            self.email_container.show()
        else:
            self.email_input.clear()
            self.email_container.hide()

    def handle_back_click(self):
        if self.on_close_callback: self.on_close_callback(False)

    def handle_save(self):
        import airtable_api
        fn = self.fullname_input.text().strip()
        un = self.username_input.text().strip()
        ps = self.password_input.text().strip()
        pin = self.pincode_input.text().strip()
        role = self.role_combobox.currentText()
        email = self.email_input.text().strip()

        if not fn or not un or not ps or not pin:
            show_safe_message(self, QMessageBox.Warning, "Validation Error", "All general fields are mandatory.")
            return

        if role == "Maneger" and not email:
            show_safe_message(self, QMessageBox.Critical, "Email Required", "Managers must provide an email address for alerts.")
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
            show_safe_message(self, QMessageBox.Critical, "Database Error", str(e))


class UserManagementPage(QWidget):
    """ Central Hub dashboard managing nested account table matrices and formatted disposal inventory grids. """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.init_ui()

    def init_ui(self):
        self.outer_stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.outer_stack)

        self.main_view_widget = QWidget()
        view_layout = QVBoxLayout(self.main_view_widget)
        view_layout.setContentsMargins(8, 8, 8, 8)
        view_layout.setSpacing(8)

        container = QFrame()
        container.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(8)

        navigation_tabs = QHBoxLayout()
        navigation_tabs.setSpacing(10)

        self.tab_users_btn = QPushButton("Staff Accounts")
        self.tab_users_btn.setCheckable(True)
        self.tab_users_btn.setChecked(True)
        self.tab_users_btn.setMinimumHeight(36)
        self.tab_users_btn.setStyleSheet(self.get_tab_style(active=True))
        self.tab_users_btn.clicked.connect(lambda: self.switch_admin_tab(0))

        self.tab_meds_btn = QPushButton("Disposal Inventory")
        self.tab_meds_btn.setCheckable(True)
        self.tab_meds_btn.setMinimumHeight(36)
        self.tab_meds_btn.setStyleSheet(self.get_tab_style(active=False))
        self.tab_meds_btn.clicked.connect(lambda: self.switch_admin_tab(1))

        self.add_staff_fab = QPushButton("Add New Staff")
        self.add_staff_fab.setMinimumHeight(36)
        self.add_staff_fab.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 8px 20px; border-radius: 8px; font-size: 15px; border: none;")
        self.add_staff_fab.clicked.connect(self.navigate_to_add_form)

        back_btn = QPushButton("Menu")
        back_btn.setMinimumHeight(36)
        back_btn.setStyleSheet(
            "padding: 8px 18px; background-color: #F1F5F9; border-radius: 8px; font-weight: bold; border: 1px solid #E2E8F0; color: #475569; font-size: 15px;")
        back_btn.clicked.connect(self.on_back_to_menu)

        navigation_tabs.addWidget(self.tab_users_btn)
        navigation_tabs.addWidget(self.tab_meds_btn)
        navigation_tabs.addWidget(self.add_staff_fab)
        navigation_tabs.addStretch()
        navigation_tabs.addWidget(back_btn)

        navigation_widget = QWidget()
        navigation_widget.setLayout(navigation_tabs)
        navigation_widget.setMinimumWidth(650)
        navigation_scroll = make_scroll_area(navigation_widget)
        navigation_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        navigation_scroll.setMaximumHeight(58)
        container_layout.addWidget(navigation_scroll)

        self.admin_sub_stack = QStackedWidget()

        # Tab Index 0: Staff Users Grid Widget
        self.page_users_widget = QTableWidget()
        self.page_users_widget.setColumnCount(4)
        self.page_users_widget.setHorizontalHeaderLabels(["Username", "Role", "Email Contact", "Actions"])
        self.page_users_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.page_users_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.page_users_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.page_users_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.page_users_widget.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.page_users_widget.setStyleSheet(self.get_table_style())

        header_u = self.page_users_widget.horizontalHeader()
        header_u.setSectionResizeMode(0, QHeaderView.Stretch)
        header_u.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_u.setSectionResizeMode(2, QHeaderView.Stretch)
        header_u.setSectionResizeMode(3, QHeaderView.Fixed)
        self.page_users_widget.setColumnWidth(3, 170)
        self.page_users_widget.verticalHeader().setDefaultSectionSize(50)
        self.admin_sub_stack.addWidget(self.page_users_widget)

        # Tab Index 1: Disposal Inventory Table Widget
        self.page_meds_table = QTableWidget()
        self.page_meds_table.setColumnCount(5)
        self.page_meds_table.setHorizontalHeaderLabels(
            ["Expiry Date", "Medicine Name", "Batch Number", "Quantity", "Actions"])
        self.page_meds_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.page_meds_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.page_meds_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.page_meds_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.page_meds_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.page_meds_table.setStyleSheet(self.get_table_style())

        header_m = self.page_meds_table.horizontalHeader()
        header_m.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_m.setSectionResizeMode(1, QHeaderView.Stretch)
        header_m.setSectionResizeMode(2, QHeaderView.Stretch)
        header_m.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_m.setSectionResizeMode(4, QHeaderView.Fixed)

        # 🔥 UX Optimization: Increased column width to 190px to comfortably hold the new text
        self.page_meds_table.setColumnWidth(4, 160)
        self.page_meds_table.verticalHeader().setDefaultSectionSize(50)
        self.admin_sub_stack.addWidget(self.page_meds_table)

        container_layout.addWidget(self.admin_sub_stack)

        self.refresh_hub_btn = QPushButton("Sync Cloud Directory")
        self.refresh_hub_btn.setMinimumHeight(36)
        self.refresh_hub_btn.setStyleSheet(
            "padding: 10px; font-size: 14px; font-weight: bold; background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; color: #475569;")
        self.refresh_hub_btn.clicked.connect(self.sync_current_hub_view)
        container_layout.addWidget(self.refresh_hub_btn)

        self.go_back_tab_btn = QPushButton("Go Back to Staff Accounts")
        self.go_back_tab_btn.setMinimumHeight(36)
        self.go_back_tab_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.go_back_tab_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #475569; font-weight: bold; font-size: 14px; border: 1px solid #E2E8F0; border-radius: 8px; }
            QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }
        """)
        self.go_back_tab_btn.clicked.connect(lambda: self.switch_admin_tab(0))
        container_layout.addWidget(self.go_back_tab_btn)
        self.go_back_tab_btn.hide()

        main_scroll = make_scroll_area(container)
        view_layout.addWidget(main_scroll)
        self.outer_stack.addWidget(self.main_view_widget)

        self.form_page_widget = StaffFormPage(self, on_close_callback=self.handle_form_callback)
        self.outer_stack.addWidget(self.form_page_widget)

        self.switch_admin_tab(0)

    def showEvent(self, event):
        super().showEvent(event)
        if self.outer_stack.currentIndex() == 0:
            self.sync_current_hub_view()

    def navigate_to_add_form(self):
        self.form_page_widget.set_user_data(None)
        self.outer_stack.setCurrentWidget(self.form_page_widget)

    def navigate_to_edit_form(self, user_data):
        self.form_page_widget.set_user_data(user_data)
        self.outer_stack.setCurrentWidget(self.form_page_widget)

    def handle_form_callback(self, is_saved):
        self.outer_stack.setCurrentIndex(0)
        if is_saved:
            show_safe_message(self, QMessageBox.Information, "Success", "Database synchronized successfully.")
            self.load_users_data()

    def switch_admin_tab(self, index):
        self.admin_sub_stack.setCurrentIndex(index)
        if index == 0:
            self.tab_users_btn.setChecked(True)
            self.tab_users_btn.setStyleSheet(self.get_tab_style(active=True))
            self.tab_meds_btn.setChecked(False)
            self.tab_meds_btn.setStyleSheet(self.get_tab_style(active=False))
            self.add_staff_fab.show()
            self.go_back_tab_btn.hide()
            self.load_users_data()
        else:
            self.tab_users_btn.setChecked(False)
            self.tab_users_btn.setStyleSheet(self.get_tab_style(active=False))
            self.tab_meds_btn.setChecked(True)
            self.tab_meds_btn.setStyleSheet(self.get_tab_style(active=True))
            self.add_staff_fab.hide()
            self.go_back_tab_btn.show()
            self.load_inventory_disposal_data()

    def sync_current_hub_view(self):
        if self.admin_sub_stack.currentIndex() == 0:
            self.load_users_data()
        else:
            self.load_inventory_disposal_data()

    def load_users_data(self):
        import airtable_api
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
                email_str = str(email_val)
                if len(email_str) > 28: email_str = email_str[:25] + "..."
                e_item = QTableWidgetItem(email_str)

                u_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                r_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                e_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                self.page_users_widget.setItem(row_idx, 0, u_item)
                self.page_users_widget.setItem(row_idx, 1, r_item)
                self.page_users_widget.setItem(row_idx, 2, e_item)

                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 6, 6, 6)
                actions_layout.setSpacing(10)

                edit_btn = QPushButton("Edit")
                edit_btn.setFixedSize(72, 34)
                edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
                edit_btn.setStyleSheet(
                    "background-color: #0EA5E9; color: white; border-radius: 6px; border: none; font-size: 14px; font-weight: bold;")
                edit_btn.clicked.connect(lambda checked, u=user_data: self.navigate_to_edit_form(u))

                del_btn = QPushButton("Delete")
                del_btn.setFixedSize(78, 34)
                del_btn.setCursor(QCursor(Qt.PointingHandCursor))
                del_btn.setStyleSheet(
                    "background-color: #EF4444; color: white; border-radius: 6px; border: none; font-size: 14px; font-weight: bold;")
                del_btn.clicked.connect(lambda checked, u=user_data: self.handle_delete_user(u))

                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(del_btn)
                actions_layout.addStretch()
                self.page_users_widget.setCellWidget(row_idx, 3, actions_widget)
        except Exception as e:
            print(f"Error table sync: {e}")

    def handle_delete_user(self, user_data):
        import airtable_api
        username = user_data.get("Username", "Unknown")
        confirm = ask_safe_confirmation(self, QMessageBox.Warning, "Delete Staff Account",
                                        f"Are you sure you want to permanently delete staff account '{username}'?")
        if confirm:
            try:
                if airtable_api.delete_user_record(user_data.get("record_id")):
                    show_safe_message(self, QMessageBox.Information, "Deleted", f"Account '{username}' removed completely.")
                    self.load_users_data()
            except Exception as e:
                show_safe_message(self, QMessageBox.Critical, "Database Error", str(e))

    def load_inventory_disposal_data(self):
        import airtable_api
        self.page_meds_table.setRowCount(0)
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
                        "batch": fields.get("A Batch", "N/A") or fields.get("Batch Number", "N/A"),
                        "expiry": fields.get("Expiry Date", "9999-12-31"),
                        "qty": qty
                    })
            cached_meds.sort(key=lambda x: x['expiry'])

            for row_idx, med in enumerate(cached_meds):
                self.page_meds_table.insertRow(row_idx)

                exp_item = QTableWidgetItem(str(med['expiry']))
                name_item = QTableWidgetItem(str(med['name']))
                batch_item = QTableWidgetItem(str(med['batch']))
                qty_item = QTableWidgetItem(str(med['qty']))

                exp_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                batch_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                qty_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                qty_item.setTextAlignment(Qt.AlignCenter)

                self.page_meds_table.setItem(row_idx, 0, exp_item)
                self.page_meds_table.setItem(row_idx, 1, name_item)
                self.page_meds_table.setItem(row_idx, 2, batch_item)
                self.page_meds_table.setItem(row_idx, 3, qty_item)

                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 6, 6, 6)

                # 🔥 Refactored: Changed text to 'Discard Medicine' for complete semantic understanding
                discard_btn = QPushButton("🗑️ Discard Medicine")
                discard_btn.setFixedSize(140, 34)
                discard_btn.setCursor(QCursor(Qt.PointingHandCursor))
                discard_btn.setStyleSheet("""
                    QPushButton { background-color: #EF4444; color: white; border-radius: 6px; font-weight: bold; font-size: 14px; border: none; }
                    QPushButton:hover { background-color: #DC2626; }
                """)
                discard_btn.clicked.connect(lambda checked, m=med: self.execute_emergency_medicine_purge(m))

                actions_layout.addWidget(discard_btn)
                actions_layout.addStretch()
                self.page_meds_table.setCellWidget(row_idx, 4, actions_widget)

        except Exception as e:
            print(f"Error inventory sync: {e}")

    def execute_emergency_medicine_purge(self, med_data):
        import airtable_api
        confirm = ask_safe_confirmation(self, QMessageBox.Critical, "Emergency Discard",
                                        f"Are you sure you want to permanently discard batch '{med_data['batch']}' for '{med_data['name']}'?")
        if confirm:
            try:
                if airtable_api.delete_medication_record(med_data["id"]):
                    airtable_api.log_transaction("ADMIN_PURGE_DELETE", med_data["barcode"], "System Manager",
                                                 med_data["qty"], "Manager Portal Emergency Disposal")
                    show_safe_message(self, QMessageBox.Information, "Discarded", "Batch deleted successfully.")
                    self.load_inventory_disposal_data()
            except Exception as e:
                show_safe_message(self, QMessageBox.Critical, "Server Error", str(e))

    def get_tab_style(self, active=True):
        if active: return "background-color: #6366F1; color: white; font-weight: bold; padding: 8px 20px; border-radius: 8px; font-size: 15px; border: none;"
        return "background-color: #F1F5F9; color: #475569; font-weight: bold; padding: 8px 20px; border-radius: 8px; font-size: 15px; border: 1px solid #E2E8F0;"

    def get_table_style(self):
        return """
            QTableWidget { background-color: #FFFFFF; color: #334155; font-size: 13px; border: 1px solid #E2E8F0; border-radius: 8px; }
            QHeaderView::section { background-color: #F8FAFC; font-weight: bold; border: none; padding: 7px; color: #64748B; font-size: 13px; border-bottom: 1px solid #E2E8F0; }
            QTableWidget::item { padding: 7px; border-bottom: 1px solid #F1F5F9; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 35px; border-radius: 7px; }
            QScrollBar:horizontal { border: none; background: #F1F5F9; height: 14px; margin: 0px; border-radius: 7px; }
            QScrollBar::handle:horizontal { background: #CBD5E1; min-width: 35px; border-radius: 7px; }
            QTableWidget::item:selected { background-color: #EEF2FF; color: #4F46E5; font-weight: bold; }
        """