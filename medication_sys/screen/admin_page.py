import sys
import os

# إعلام بايثون بالمسار الرئيسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QFrame, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


class UserManagementPage(QWidget):
    """ Modernized & Touch-Optimized Admin Panel Workspace with Dynamic Trigger Keyboard """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.editing_record_id = None
        self.current_focused_input = None
        self.init_ui()

    def init_ui(self):
        # تطبيق ستايل عام فخم ومريح للعين بمقاسات مضغوطة تلائم الرازبري باي
        self.setStyleSheet("""
            QWidget { 
                background-color: #F8FAFC; 
                font-family: 'Segoe UI', Arial, sans-serif; 
                color: #1E293B; 
            }
            QLabel { 
                font-size: 11px; 
                font-weight: 600; 
                color: #475569; 
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 11px;
                background-color: #F8FAFC;
            }
            QComboBox { 
                padding: 6px; 
                border: 1px solid #E2E8F0; 
                border-radius: 6px; 
                background-color: #FFFFFF; 
                font-size: 11px;
            }
            QComboBox:focus { border: 2px solid #6366F1; }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)  # هوامش ضيقة للشاشة الصغيرة
        main_layout.setSpacing(10)

        # =====================================================================
        # 📊 LEFT SIDE: Directory Table View (Card Style)
        # =====================================================================
        left_container = QFrame()
        left_container.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        table_title = QLabel("👥 Active Staff Directory")
        table_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #0F172A; border: none; background: transparent;")

        back_btn = QPushButton("⬅️ Back")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton { 
                padding: 4px 10px; background-color: #F1F5F9; border-radius: 6px; 
                font-weight: bold; border: 1px solid #E2E8F0; color: #475569; font-size: 11px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.reset_form_state)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(table_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        # تصميم الجدول بشكل مودرن مدمج للرازبري
        self.users_table_widget = QTableWidget()
        self.users_table_widget.setColumnCount(3)
        self.users_table_widget.setHorizontalHeaderLabels(["Username", "Role", "Actions"])
        self.users_table_widget.setFrameShape(QFrame.NoFrame)
        self.users_table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table_widget.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.users_table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.users_table_widget.setColumnWidth(2, 90)  # تقليص العرض للأزرار
        self.users_table_widget.verticalHeader().setDefaultSectionSize(28)  # تقليل ارتفاع السجل للبرس بلمسة

        self.users_table_widget.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; color: #334155; font-size: 11px; }
            QHeaderView::section { 
                background-color: #F8FAFC; font-weight: bold; border: none; 
                padding: 6px; color: #64748B; font-size: 11px; border-bottom: 2px solid #E2E8F0;
            }
            QTableWidget::item { padding: 4px; border-bottom: 1px solid #F1F5F9; }
            QTableWidget::item:selected { background-color: #EEF2FF; color: #4F46E5; }
        """)
        left_layout.addWidget(self.users_table_widget)

        refresh_btn = QPushButton("🔄 Refresh Server Directory")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("""
            QPushButton { 
                padding: 8px; font-size: 12px; font-weight: bold; background-color: #F8FAFC; 
                border: 1px solid #CBD5E1; border-radius: 8px; color: #475569;
            }
            QPushButton:hover { background-color: #F1F5F9; }
        """)
        refresh_btn.clicked.connect(self.load_users_data)
        left_layout.addWidget(refresh_btn)
        main_layout.addWidget(left_container, stretch=5)

        # =====================================================================
        # 📝 RIGHT SIDE: Operations & Input Form Card
        # =====================================================================
        right_container = QFrame()
        right_container.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(4)

        self.form_title = QLabel("Register New System Account")
        self.form_title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #4F46E5; margin-bottom: 2px; border: none; background: transparent;")
        right_layout.addWidget(self.form_title)

        right_layout.addWidget(QLabel("Full Name"))
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("John Doe")
        self.fullname_input.focusInEvent = lambda event: self.handle_input_focus(self.fullname_input, event)
        right_layout.addWidget(self.fullname_input)

        right_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("johndoe12")
        self.username_input.focusInEvent = lambda event: self.handle_input_focus(self.username_input, event)
        right_layout.addWidget(self.username_input)

        right_layout.addWidget(QLabel("Password / Security Key"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter secure text key")
        self.password_input.focusInEvent = lambda event: self.handle_input_focus(self.password_input, event)
        right_layout.addWidget(self.password_input)

        right_layout.addWidget(QLabel("System PIN Code"))
        self.pincode_input = QLineEdit()
        self.pincode_input.setPlaceholderText("e.g. 1234")
        self.pincode_input.focusInEvent = lambda event: self.handle_input_focus(self.pincode_input, event)
        right_layout.addWidget(self.pincode_input)

        right_layout.addWidget(QLabel("System Privilege Level"))
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["Maneger", "Doctor", "Nurse", "Assistant"])
        right_layout.addWidget(self.role_combobox)

        self.submit_btn = QPushButton("➕ Confirm Access Registration")
        self.submit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4F46E5; color: white; padding: 10px; 
                font-weight: bold; border-radius: 8px; border: none; font-size: 12px; margin-top: 2px;
            }
            QPushButton:pressed { background-color: #4338CA; }
        """)
        self.submit_btn.clicked.connect(self.handle_save_user)
        right_layout.addWidget(self.submit_btn)

        self.cancel_edit_btn = QPushButton("❌ Cancel Form Editing")
        self.cancel_edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cancel_edit_btn.setStyleSheet("""
            QPushButton { background-color: #EF4444; color: white; padding: 6px; font-weight: 600; border-radius: 8px; border: none; font-size: 11px; }
            QPushButton:pressed { background-color: #DC2626; }
        """)
        self.cancel_edit_btn.clicked.connect(self.reset_form_state)
        self.cancel_edit_btn.hide()
        right_layout.addWidget(self.cancel_edit_btn)

        # =====================================================================
        # ⌨️ EMBEDDED VIRTUAL KEYBOARD (Premium Styled)
        # =====================================================================
        right_layout.addWidget(QLabel("Touch Entry Pad:"))
        self.keyboard_widget = QWidget()
        self.keyboard_widget.setStyleSheet("border: none; background: transparent;")
        keyboard_layout = QVBoxLayout(self.keyboard_widget)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.setSpacing(3)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', '⌫', '🔽 Hide']
        ]

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(3)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setCursor(QCursor(Qt.PointingHandCursor))
                if key in ['Clear', '⌫', '🔽 Hide']:
                    btn.setStyleSheet("""
                        QPushButton { 
                            background-color: #CBD5E1; color: #1E293B; font-weight: bold; 
                            padding: 10px 2px; border-radius: 4px; border: none; font-size: 11px; 
                        }
                        QPushButton:pressed { background-color: #94A3B8; }
                    """)
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet("""
                        QPushButton { 
                            background-color: #F1F5F9; color: #1E293B; font-weight: bold; 
                            padding: 10px 2px; border-radius: 4px; border: 1px solid #E2E8F0; min-width: 40px; font-size: 11px; 
                        }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { 
                            background-color: #F1F5F9; color: #1E293B; font-weight: 600; 
                            padding: 10px 2px; border-radius: 4px; border: 1px solid #E2E8F0; font-size: 11px; 
                        }
                        QPushButton:pressed { background-color: #E2E8F0; }
                    """)
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                row_layout.addWidget(btn)
            keyboard_layout.addLayout(row_layout)

        right_layout.addWidget(self.keyboard_widget)
        main_layout.addWidget(right_container, stretch=4)

        # 🔐 إخفاء الكيبورد بشكل افتراضي في البداية وتثبيت الـ Event Filters بأمان تام
        self.keyboard_widget.hide()

        self.fullname_input.installEventFilter(self)
        self.username_input.installEventFilter(self)
        self.password_input.installEventFilter(self)
        self.pincode_input.installEventFilter(self)

        self.reset_form_state()

    def handle_input_focus(self, input_field, event):
        for input_box in [self.fullname_input, self.username_input, self.password_input, self.pincode_input]:
            if input_box != input_field:
                input_box.setStyleSheet(
                    "padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 11px; background-color: #F8FAFC; color: #1E293B;")

        self.current_focused_input = input_field
        if event:
            super(QLineEdit, input_field).focusInEvent(event)

        input_field.setStyleSheet(
            "padding: 6px; border: 2px solid #6366F1; border-radius: 6px; font-size: 11px; background-color: #F5F3FF; color: #0F172A;")
        input_field.setFocus(Qt.OtherFocusReason)
        input_field.setCursorPosition(len(input_field.text()))

    def eventFilter(self, obj, event):
        # التقاط حدث النقرة أو اللمس الفعلي داخل الـ LineEdits لإظهار الكيبورد
        f_in = getattr(self, 'fullname_input', None)
        u_in = getattr(self, 'username_input', None)
        p_in = getattr(self, 'password_input', None)
        pin_in = getattr(self, 'pincode_input', None)

        if obj in [f_in, u_in, p_in, pin_in] and obj is not None:
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]:
                self.keyboard_widget.show()
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return
        current_text = self.current_focused_input.text()

        if key == '⌫':
            self.current_focused_input.setText(current_text[:-1])
        elif key == 'Clear':
            self.current_focused_input.clear()
        elif key == '🔽 Hide':
            self.keyboard_widget.hide()
            return
        else:
            self.current_focused_input.setText(current_text + key)

        self.current_focused_input.setFocus(Qt.OtherFocusReason)
        self.current_focused_input.setStyleSheet(
            "padding: 6px; border: 2px solid #6366F1; border-radius: 6px; font-size: 11px; background-color: #F5F3FF; color: #0F172A;")
        self.current_focused_input.setCursorPosition(len(self.current_focused_input.text()))

    def load_users_data(self):
        try:
            users = airtable_api.get_all_users()
            self.users_table_widget.setRowCount(0)
            for row_idx, user_data in enumerate(users):
                self.users_table_widget.insertRow(row_idx)
                role_val = user_data.get("Role", "N/A")
                if isinstance(role_val, list): role_val = role_val[0] if role_val else "N/A"

                u_item = QTableWidgetItem(str(user_data.get("Username", "N/A")))
                r_item = QTableWidgetItem(str(role_val))
                u_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                r_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                self.users_table_widget.setItem(row_idx, 0, u_item)
                self.users_table_widget.setItem(row_idx, 1, r_item)

                actions_widget = QWidget()
                actions_widget.setStyleSheet("background-color: transparent;")
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 1, 2, 1)
                actions_layout.setSpacing(4)

                edit_icon_btn = QPushButton("✏️")
                edit_icon_btn.setFixedSize(24, 24)
                edit_icon_btn.setStyleSheet("""
                    QPushButton { background-color: #0EA5E9; color: white; border-radius: 4px; font-size: 11px; border: none; }
                """)
                edit_icon_btn.clicked.connect(lambda checked, u=user_data: self.prepare_edit_user(u))

                delete_icon_btn = QPushButton("🗑️")
                delete_icon_btn.setFixedSize(24, 24)
                delete_icon_btn.setStyleSheet("""
                    QPushButton { background-color: #EF4444; color: white; border-radius: 4px; font-size: 11px; border: none; }
                """)
                delete_icon_btn.clicked.connect(lambda checked, u=user_data: self.handle_delete_user(u))

                actions_layout.addWidget(edit_icon_btn)
                actions_layout.addWidget(delete_icon_btn)
                actions_layout.addStretch()
                self.users_table_widget.setCellWidget(row_idx, 2, actions_widget)
        except Exception as e:
            print(f"Error loading table data: {str(e)}")

    def prepare_edit_user(self, user_data):
        self.editing_record_id = user_data.get("record_id")
        self.fullname_input.setText(str(user_data.get("Full Name", "")))
        self.username_input.setText(str(user_data.get("Username", "")))
        self.password_input.setText(str(user_data.get("Password", "")))
        pin_raw = str(user_data.get("PIN Code", ""))
        self.pincode_input.setText(pin_raw.split(".")[0] if "." in pin_raw else pin_raw)

        role_val = user_data.get("Role", "Assistant")
        if isinstance(role_val, list): role_val = role_val[0] if role_val else "Assistant"
        index = self.role_combobox.findText(str(role_val))
        if index >= 0: self.role_combobox.setCurrentIndex(index)

        self.form_title.setText("📝 Edit System Account")
        self.form_title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #EA580C; margin-bottom: 2px; border: none; background: transparent;")
        self.submit_btn.setText("💾 Save Modified Changes")
        self.submit_btn.setStyleSheet("""
            QPushButton { background-color: #EA580C; color: white; padding: 10px; font-weight: bold; border-radius: 8px; border: none; font-size: 12px; margin-top: 2px; }
        """)
        self.cancel_edit_btn.show()

        # عند الضغط على تعديل مستخدم، نفتح الكيبورد تلقائياً للتسهيل
        self.keyboard_widget.show()
        self.handle_input_focus(self.fullname_input, None)

    def reset_form_state(self):
        self.editing_record_id = None
        self.fullname_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.pincode_input.clear()

        for input_box in [self.fullname_input, self.username_input, self.password_input, self.pincode_input]:
            input_box.setStyleSheet(
                "padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 11px; background-color: #F8FAFC; color: #1E293B;")

        self.role_combobox.setCurrentIndex(0)

        self.form_title.setText("Register New System Account")
        self.form_title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #4F46E5; margin-bottom: 2px; border: none; background: transparent;")
        self.submit_btn.setText("➕ Confirm Access Registration")
        self.submit_btn.setStyleSheet("""
            QPushButton { background-color: #4F46E5; color: white; padding: 10px; font-weight: bold; border-radius: 8px; border: none; font-size: 12px; margin-top: 2px; }
        """)
        self.cancel_edit_btn.hide()

        # إخفاء الكيبورد عند إعادة ضبط الاستمارات
        if hasattr(self, 'keyboard_widget'):
            self.keyboard_widget.hide()

        self.handle_input_focus(self.fullname_input, None)

    def handle_save_user(self):
        full_name = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        pin_code = self.pincode_input.text().strip()
        role = self.role_combobox.currentText()

        if not full_name or not username or not password or not pin_code:
            QMessageBox.warning(self, "Validation Error", "All fields must be filled.")
            return

        try:
            if self.editing_record_id:
                confirm = QMessageBox.question(
                    self, "Confirm Changes ❓", f"Are you sure you want to update fields for user '{username}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if confirm != QMessageBox.Yes: return

                record = airtable_api.update_user_records(self.editing_record_id, username, password, role, pin_code,
                                                          full_name)
                if record:
                    QMessageBox.information(self, "Success ✅", f"Account '{username}' updated successfully.")
                    self.reset_form_state()
                    self.load_users_data()
            else:
                record = airtable_api.add_new_user(username, password, role, pin_code, full_name)
                if record:
                    QMessageBox.information(self, "Success ✅",
                                            f"Account '{username}' registered successfully to the cloud.")
                    self.reset_form_state()
                    self.load_users_data()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save user: {str(e)}")

    def handle_delete_user(self, user_data):
        username = user_data.get("Username", "Unknown")
        record_id = user_data.get("record_id")

        confirm = QMessageBox.question(
            self, "Confirm Account Deletion ⚠️",
            f"Warning! Are you sure you want to permanently delete staff account '{username}' from the system?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                if airtable_api.delete_user_record(record_id):
                    QMessageBox.information(self, "Deleted 🗑️", f"Account '{username}' removed completely.")
                    if self.editing_record_id == record_id: self.reset_form_state()
                    self.load_users_data()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Error trying to delete: {str(e)}")