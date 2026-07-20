import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QScrollArea
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor


class CheckinScreen(QWidget):
    """
    Highly readable Patient Check-In Terminal.
    Optimized for Raspberry Pi touch displays and automatic hardware QR code scanners.
    """

    def __init__(self, stack):
        super().__init__()
        self.stack = stack

        self.kiosk_stack = QStackedWidget(self)

        self.init_search_view()  # Index 0
        self.init_profile_view()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.kiosk_stack)

        self.kiosk_stack.setCurrentIndex(0)

        # تثبيت فلتر الأحداث لضمان بقاء التركيز (Focus) على حقل السريكات دائماً
        self.installEventFilter(self)

    def showEvent(self, event):
        """ بمجرد ظهور الشاشة للمستخدم، يتم تفعيل التركيز تلقائياً للحقل """
        super().showEvent(event)
        self.prepare_for_scan()

    # =====================================================================
    # 🎴 SCREEN 0: Scanner Gate & Manual Identity Sheet Block (Compact Height)
    # =====================================================================
    def init_search_view(self):
        view = QWidget()
        view.setStyleSheet("background-color: #FFFFFF; border: none; font-family: 'Segoe UI';")
        layout = QVBoxLayout(view)
        # 🔥 تقليص الهوامش العلوية لمنع تمدد الشاشة لأسفل
        layout.setContentsMargins(40, 30, 40, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        form_card = QFrame()
        form_card.setFixedWidth(560)
        form_card.setStyleSheet("background-color: #FFFFFF; border: 2px solid #E2E8F0; border-radius: 16px;")

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(35, 25, 30, 25)
        form_layout.setSpacing(10)

        header_title = QLabel("Patient Check-In")
        header_title.setStyleSheet(
            "font-size: 32px; font-weight: bold; color: #4F46E5; border: none; margin-bottom: 2px;")
        form_layout.addWidget(header_title)

        self.hidden_qr_input = QLineEdit()
        self.hidden_qr_input.setFixedWidth(1)
        self.hidden_qr_input.setStyleSheet("background: transparent; border: none; color: transparent;")
        self.hidden_qr_input.returnPressed.connect(self.process_hardware_scan_trigger)
        form_layout.addWidget(self.hidden_qr_input)

        hint_lbl = QLabel("👋 Please Scan your QR Code / Barcode directly\nor type your Personal ID below:")
        hint_lbl.setStyleSheet("font-size: 15px; font-weight: 500; color: #475569; border: none; margin-bottom: 2px;")
        hint_lbl.setWordWrap(True)
        form_layout.addWidget(hint_lbl)

        id_label = QLabel("Your Personal ID or Name:")
        id_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1E293B; border: none;")
        form_layout.addWidget(id_label)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Enter your Personal ID here...")
        self.id_input.setStyleSheet(self.get_large_input_style())
        self.id_input.returnPressed.connect(self.process_manual_check_trigger)
        form_layout.addWidget(self.id_input)

        form_layout.addSpacing(5)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        back_btn = QPushButton("Go Back")
        back_btn.setMinimumHeight(50)
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #475569; font-weight: bold; font-size: 18px; border: 1px solid #E2E8F0; border-radius: 8px; }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.exit_patient_kiosk_context)

        self.verify_btn = QPushButton("Verify Profile")
        self.verify_btn.setMinimumHeight(50)
        self.verify_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.verify_btn.setStyleSheet("""
            QPushButton { background-color: #4F46E5; color: white; font-weight: bold; font-size: 18px; border-radius: 8px; border: none; }
            QPushButton:hover { background-color: #4338CA; }
        """)
        self.verify_btn.clicked.connect(self.process_manual_check_trigger)

        btn_layout.addWidget(back_btn, stretch=1)
        btn_layout.addWidget(self.verify_btn, stretch=2)
        form_layout.addLayout(btn_layout)

        layout.addWidget(form_card, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.kiosk_stack.addWidget(view)

    # =====================================================================
    # 🎴 SCREEN 1: Top Navigation Panel & Scroll Content Layout
    # =====================================================================
    def init_profile_view(self):
        view = QWidget()
        view.setStyleSheet("background-color: #F8FAFC; border: none; font-family: 'Segoe UI';")

        outer_layout = QVBoxLayout(view)
        # 🔥 تقليل هوامش نافذة التفاصيل
        outer_layout.setContentsMargins(15, 15, 15, 15)
        outer_layout.setSpacing(10)

        # 🔥 تحسين الملاحة: نقل الأزرار إلى الأعلى بجانب عنوان الترحيب لحماية الـ UX من الاختفاء
        top_header_layout = QHBoxLayout()

        self.welcome_title = QLabel("Welcome Back!")
        self.welcome_title.setStyleSheet("font-size: 26px; font-weight: bold; color: #4F46E5;")
        top_header_layout.addWidget(self.welcome_title)
        top_header_layout.addStretch()

        # زر الرجوع المباشر لشاشة المسح والـ QR Code (تم نقله للأعلى)
        back_to_scan_btn = QPushButton("⬅️ Back to Scanner")
        back_to_scan_btn.setFixedSize(160, 44)
        back_to_scan_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_to_scan_btn.setStyleSheet("""
            QPushButton { background-color: #FFFFFF; color: #475569; font-weight: bold; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 8px; }
            QPushButton:hover { background-color: #F1F5F9; }
        """)
        back_to_scan_btn.clicked.connect(self.return_to_scanner_screen)
        top_header_layout.addWidget(back_to_scan_btn)

        # زر إنهاء المعاينة والخروج (تم نقله للأعلى)
        close_action_btn = QPushButton("Done & Close")
        close_action_btn.setFixedSize(140, 44)
        close_action_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_action_btn.setStyleSheet("""
            QPushButton { background-color: #4F46E5; color: white; font-weight: bold; font-size: 14px; border-radius: 8px; border: none; }
            QPushButton:hover { background-color: #4338CA; }
        """)
        close_action_btn.clicked.connect(self.exit_patient_kiosk_context)
        top_header_layout.addWidget(close_action_btn)

        outer_layout.addLayout(top_header_layout)

        # حاوية التمرير للبيانات
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")

        self.card_layout = QVBoxLayout(scroll_content)
        self.card_layout.setContentsMargins(25, 20, 25, 20)
        self.card_layout.setSpacing(14)

        self.lbl_id = self.create_profile_data_row("Personal ID:")
        self.lbl_name = self.create_profile_data_row("Full Name:")
        self.lbl_lang = self.create_profile_data_row("Language Preference:")
        self.lbl_dob = self.create_profile_data_row("Date of Birth:")
        self.lbl_phone = self.create_profile_data_row("Phone Number:")
        self.lbl_gender = self.create_profile_data_row("Gender Signature:")
        self.lbl_type = self.create_profile_data_row("Identification Type:")
        self.lbl_emergency = self.create_profile_data_row("Emergency Contact info:", word_wrap=True)
        self.lbl_city = self.create_profile_data_row("City Status Context:")
        self.lbl_referred = self.create_profile_data_row("Referred by Channel:")
        self.lbl_notes = self.create_profile_data_row("Clinical Secretary Notes:", word_wrap=True)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

        self.kiosk_stack.addWidget(view)

    def create_profile_data_row(self, title_text, word_wrap=False):
        row_widget = QWidget()
        row_widget.setStyleSheet("border: none; background: transparent;")
        row_widget_layout = QHBoxLayout(row_widget)
        row_widget_layout.setContentsMargins(0, 2, 0, 2)
        row_widget_layout.setSpacing(15)

        title_lbl = QLabel(title_text)
        title_lbl.setFixedWidth(190)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #475569;")

        value_lbl = QLabel("-")
        value_lbl.setStyleSheet("font-size: 15px; font-weight: 500; color: #0F172A;")
        if word_wrap:
            value_lbl.setWordWrap(True)
            value_lbl.setStyleSheet("font-size: 15px; font-weight: 500; color: #0F172A; line-height: 18px;")

        row_widget_layout.addWidget(title_lbl, alignment=Qt.AlignTop)
        row_widget_layout.addWidget(value_lbl, stretch=1, alignment=Qt.AlignTop)

        self.card_layout.addWidget(row_widget)
        return value_lbl

    # =====================================================================
    # 🧠 BACKEND LOOKUP ENGINE & COMPONENT TRANSITIONS
    # =====================================================================
    def eventFilter(self, obj, event):
        if self.kiosk_stack.currentIndex() == 0:
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.WindowActivate]:
                if not self.id_input.hasFocus():
                    self.hidden_qr_input.setFocus(Qt.OtherFocusReason)
        return super().eventFilter(obj, event)

    def prepare_for_scan(self):
        self.id_input.clear()
        self.hidden_qr_input.clear()
        self.hidden_qr_input.setFocus(Qt.OtherFocusReason)
        self.hidden_qr_input.activateWindow()

    def process_hardware_scan_trigger(self):
        scanned_data = self.hidden_qr_input.text().strip()
        if scanned_data:
            self.execute_database_verification_query(target_id=scanned_data)

    def process_manual_check_trigger(self):
        manual_id = self.id_input.text().strip()
        if not manual_id:
            QMessageBox.warning(self, "Input Required ⚠️", "Please type your Personal ID card identity digits.")
            return
        self.execute_database_verification_query(target_id=manual_id)

    def execute_database_verification_query(self, target_id):
        try:
            from pyairtable import Api
            import config

            raw_token = getattr(config, 'AIRTOTAL_TOKEN', None) or getattr(config, 'AIRTABLE_TOKEN', None) or os.getenv(
                'AIRTABLE_TOKEN')
            raw_base_id = getattr(config, 'BASE_ID', None) or os.getenv('BASE_ID')

            if not raw_token or not raw_base_id:
                QMessageBox.critical(self, "Configuration Error ❌", "Could not resolve Airtable credentials.")
                self.prepare_for_scan()
                return

            clean_token = str(raw_token).replace('"', '').replace("'", "").strip()
            clean_base_id = str(raw_base_id).replace('"', '').replace("'", "").strip()

            api = Api(clean_token)
            patients_table = api.table(clean_base_id, "Patients")

            # Clean the input and escape characters used inside Airtable formulas.
            clean_search = str(target_id).strip()
            escaped_search = (
                clean_search
                .replace("\\", "\\\\")
                .replace("'", "\\'")
            )

            # Exact match only:
            # - Full name must match completely, ignoring upper/lower case.
            # - Personal ID must match completely.
            # Partial names such as only first name or last name are rejected.
            formula = (
                "OR("
                f"LOWER(TRIM({{Name}})) = LOWER(TRIM('{escaped_search}')),"
                f"LOWER(TRIM({{Personal ID}} & '')) = LOWER(TRIM('{escaped_search}'))"
                ")"
            )

            records = patients_table.all(formula=formula)

            if records:
                fields = records[0].get('fields', {})
                self.welcome_title.setText(f"Welcome, {fields.get('Name', 'Patient')}!")

                raw_lang = fields.get('Language', '-')
                if isinstance(raw_lang, list) and len(raw_lang) > 0:
                    raw_lang = raw_lang[0]

                self.lbl_id.setText(str(fields.get('Personal ID', '-')))
                self.lbl_name.setText(str(fields.get('Name', '-')))
                self.lbl_lang.setText(str(raw_lang))
                self.lbl_dob.setText(str(fields.get('Date of Birth', '-')))
                self.lbl_phone.setText(str(fields.get('Phone', '-')))
                self.lbl_gender.setText(str(fields.get('Gender', '-')))
                self.lbl_type.setText(str(fields.get('ID Type', '-')))
                self.lbl_emergency.setText(str(fields.get('Emergy contact', '-')))
                self.lbl_city.setText(str(fields.get('City \\\\ Unhoused', '-')))
                self.lbl_referred.setText(str(fields.get('Referred by', '-')))
                self.lbl_notes.setText(str(fields.get('Notes', '-')))

                self.kiosk_stack.setCurrentIndex(1)
            else:
                QMessageBox.critical(self, "Profile Not Found ❌",
                                     f"No registered profile discovered matching identity: {target_id}\nPlease step over to the Medical Secretary desk.")
                self.prepare_for_scan()

        except Exception as e:
            QMessageBox.critical(self, "Cloud Error ❌", f"Failed connection diagnostics loop:\n{str(e)}")
            self.prepare_for_scan()

    def return_to_scanner_screen(self):
        self.kiosk_stack.setCurrentIndex(0)
        self.prepare_for_scan()

    def exit_patient_kiosk_context(self):
        self.id_input.clear()
        self.hidden_qr_input.clear()
        self.kiosk_stack.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    def get_large_input_style(self):
        return """
            QLineEdit {
                padding: 10px;
                border: 2px solid #CBD5E1;
                border-radius: 8px;
                font-size: 15px;
                background-color: #F8FAFC;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 2px solid #4F46E5;
                background-color: #EEF2FF;
                font-weight: bold;
            }
        """