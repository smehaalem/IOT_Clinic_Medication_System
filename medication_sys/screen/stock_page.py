import sys
import os
from datetime import datetime
from calendar import monthrange

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QDateEdit, QSpinBox,
    QDialog, QListWidget, QListWidgetItem, QComboBox, QScrollArea, QSizePolicy, QLayout, QGridLayout
)

from PyQt5.QtCore import Qt, QDate, QEvent, QTimer
from PyQt5.QtGui import QCursor, QIntValidator
import airtable_api


def _position_custom_close_button(dialog):
    button = getattr(dialog, "_custom_close_button", None)
    if button is None:
        return

    button.move(max(6, dialog.width() - button.width() - 8), 8)
    button.raise_()


def add_custom_close_button(dialog):
    """
    Add an in-app X button so Raspberry Pi's window manager cannot add
    minimize and maximize buttons.
    """
    button = QPushButton("X", dialog)
    button.setObjectName("customDialogCloseButton")
    button.setFixedSize(30, 28)
    button.setCursor(QCursor(Qt.PointingHandCursor))
    button.setFocusPolicy(Qt.NoFocus)
    button.setStyleSheet("""
        QPushButton#customDialogCloseButton {
            background-color: transparent;
            color: #64748B;
            border: none;
            font-size: 16px;
            font-weight: bold;
        }

        QPushButton#customDialogCloseButton:hover {
            background-color: #FEE2E2;
            color: #DC2626;
            border-radius: 6px;
        }

        QPushButton#customDialogCloseButton:pressed {
            background-color: #FECACA;
            color: #991B1B;
        }
    """)
    button.clicked.connect(dialog.reject)

    dialog._custom_close_button = button

    QTimer.singleShot(0, lambda: _position_custom_close_button(dialog))
    QTimer.singleShot(80, lambda: _position_custom_close_button(dialog))


def make_dialog_kiosk_safe(dialog):
    # Remove the operating-system title bar completely.
    # This guarantees that Raspberry Pi cannot add minimize/maximize buttons.
    flags = (
        Qt.Dialog
        | Qt.FramelessWindowHint
        | Qt.WindowStaysOnTopHint
    )
    dialog.setWindowFlags(flags)
    dialog.setWindowModality(Qt.ApplicationModal)
    add_custom_close_button(dialog)


def keep_dialog_visible(dialog):
    try:
        dialog.showNormal()
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        pass


def show_safe_message(parent, icon, title, text):
    # These validation and warning popups use the same custom frameless
    # design with only an in-app X button.
    custom_titles = {
        "Input Error",
        "Selection Required",
        "Error",
        "Expired Medication",
    }

    if title in custom_titles:
        dialog = QDialog(parent)
        dialog.setFixedWidth(400)
        dialog.setWindowTitle(title)
        make_dialog_kiosk_safe(dialog)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 42, 20, 18)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_color = "#DC2626" if title in {
            "Input Error",
            "Error",
            "Expired Medication",
        } else "#EA580C"

        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; "
            f"color: {title_color};"
        )
        layout.addWidget(title_label)

        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet(
            "font-size: 14px; color: #1E293B; line-height: 20px;"
        )
        layout.addWidget(message_label)

        ok_button = QPushButton("OK")
        ok_button.setMinimumHeight(40)
        ok_button.setCursor(QCursor(Qt.PointingHandCursor))
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #4338CA;
            }

            QPushButton:pressed {
                background-color: #3730A3;
            }
        """)
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
        """)

        QTimer.singleShot(0, lambda: keep_dialog_visible(dialog))
        QTimer.singleShot(0, lambda: _position_custom_close_button(dialog))
        return dialog.exec_()

    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    make_dialog_kiosk_safe(box)
    box.setStyleSheet("""
        QMessageBox {
            background-color: #F8FAFC;
        }

        QMessageBox QLabel {
            padding-top: 18px;
            color: #1E293B;
        }
    """)
    QTimer.singleShot(0, lambda: keep_dialog_visible(box))
    QTimer.singleShot(0, lambda: _position_custom_close_button(box))
    return box.exec_()


class BatchSelectionDialog(QDialog):
    """ ????? ?????? ???? ???? ???????? ??? ????? ???? ????? ?? ????? ???? ????? """

    def __init__(self, batches, parent=None):
        super().__init__(parent)
        self.setWindowTitle("available stock")
        self.setFixedWidth(440)
        make_dialog_kiosk_safe(self)
        self.selected_batch = None
        self.action_type = None  # "edit" or "new"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 42, 15, 15)

        title = QLabel("available stock found")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0EA5E9;")
        layout.addWidget(title)

        desc = QLabel(
            "We found available stock for this medicine.\nSelect to EDIT or choose to create a NEW one:")
        desc.setStyleSheet("font-size: 14px; color: #475569;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setMinimumHeight(130)
        self.list_widget.setMaximumHeight(220)
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #E2E8F0; border-radius: 8px; font-size: 14px; padding: 6px; background-color: #F8FAFC; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #F1F5F9; color: #1E293B; }
            QListWidget::item:selected { background-color: #F0F9FF; color: #0369A1; font-weight: bold; }
        """)

        for b in batches:
            expiry_display = self.format_expiry_for_display(b.get("expiry_date", ""))
            item_text = f"Batch: {b['batch_number']} | Exp: {expiry_display} | Qty: {b['current_quantity']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, b)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        edit_btn = QPushButton("Edit selected")
        edit_btn.setMinimumHeight(36)
        edit_btn.setStyleSheet(
            "background-color: #EA580C; color: white; font-size: 14px; font-weight: bold; border-radius: 8px; border: none;")
        edit_btn.clicked.connect(self.on_edit_clicked)

        new_batch_btn = QPushButton("New")
        new_batch_btn.setMinimumHeight(36)
        new_batch_btn.setStyleSheet(
            "background-color: #0D9488; color: white; font-size: 14px; font-weight: bold; border-radius: 8px; border: none;")
        new_batch_btn.clicked.connect(self.on_new_clicked)

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(new_batch_btn)
        layout.addLayout(btn_layout)

    @staticmethod
    def format_expiry_for_display(expiry_value):
        date_value = QDate.fromString(str(expiry_value), "yyyy-MM-dd")
        if date_value.isValid():
            return date_value.toString("MM/yyyy")
        return str(expiry_value)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, lambda: keep_dialog_visible(self))
        super().changeEvent(event)

    def on_edit_clicked(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            show_safe_message(self, QMessageBox.Warning, "Selection Required", "Please select a batch to edit.")
            return
        self.selected_batch = current_item.data(Qt.UserRole)
        self.action_type = "edit"
        self.accept()

    def on_new_clicked(self):
        self.action_type = "new"
        self.accept()


class MedicationManagementPage(QWidget):
    """
    Modern Restock Controller supporting BOTH Barcode Scanning and Medicine Name Verification.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.current_user_record_id = None
        self.current_focused_input = None
        self.existing_record_id = None

        # Stores the real barcode when an existing medicine is found by name.
        # This prevents new batches created through name search from being
        # saved as NO_BARCODE.
        self.resolved_barcode = None

        self.internal_stack = QStackedWidget(self)

        self.init_scan_page()  # Index 0
        self.init_form_page()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)
        QTimer.singleShot(150, self.focus_stock_barcode_input)

    def _make_scroll_area(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 35px; border-radius: 7px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        scroll.setWidget(widget)
        return scroll

    def set_current_user(self, user_record_id):
        self.current_user_record_id = user_record_id

    @staticmethod
    def extract_barcode_from_fields(fields):
        """Return a clean barcode from the possible Airtable barcode fields."""
        barcode_value = (
            fields.get("Barcode")
            or fields.get("Barcode lookup")
            or fields.get("Barcode (from Barcode)")
            or fields.get("Product Barcode")
            or fields.get("Barcode Number")
        )

        if isinstance(barcode_value, list):
            barcode_value = barcode_value[0] if barcode_value else ""

        clean_barcode = str(barcode_value or "").strip()

        if clean_barcode.upper() in ("", "NONE", "NO_BARCODE", "N/A"):
            return None

        return clean_barcode

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self.focus_stock_barcode_input)

    def focus_stock_barcode_input(self):
        try:
            if self.internal_stack.currentIndex() != 0:
                return
            if self.verification_mode_combo.currentText() != "Barcode":
                self.verification_mode_combo.setCurrentText("Barcode")
            self.barcode_input.setFocus(Qt.OtherFocusReason)
            self.barcode_input.selectAll()
        except Exception:
            pass


    def _move_dialog_to_upper_position(self, dialog):
        try:
            parent = self.window()
            if parent is not None:
                top_left = parent.mapToGlobal(parent.rect().topLeft())
                x = top_left.x() + max(0, (parent.width() - dialog.width()) // 2)
                y = top_left.y() + 35
            else:
                screen = dialog.screen().availableGeometry()
                x = screen.x() + max(0, (screen.width() - dialog.width()) // 2)
                y = screen.y() + 35
            dialog.move(x, y)
        except Exception:
            pass

    def ask_upper_confirmation(self, title, message):
        """
        Custom frameless confirmation dialog.

        A normal QMessageBox may still receive Raspberry Pi window-manager
        buttons. This custom QDialog has no system title bar and contains only
        our own X button.
        """
        dialog = QDialog(self)
        dialog.setFixedWidth(430)
        dialog.setWindowTitle(title)
        make_dialog_kiosk_safe(dialog)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 42, 20, 18)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #4F46E5;"
        )
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignLeft)
        message_label.setStyleSheet(
            "font-size: 14px; color: #1E293B; line-height: 20px;"
        )
        layout.addWidget(message_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        no_button = QPushButton("No")
        no_button.setMinimumHeight(40)
        no_button.setCursor(QCursor(Qt.PointingHandCursor))
        no_button.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        no_button.clicked.connect(dialog.reject)

        yes_button = QPushButton("Yes")
        yes_button.setMinimumHeight(40)
        yes_button.setCursor(QCursor(Qt.PointingHandCursor))
        yes_button.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
            QPushButton:pressed {
                background-color: #115E59;
            }
        """)
        yes_button.clicked.connect(dialog.accept)

        buttons_layout.addWidget(no_button)
        buttons_layout.addWidget(yes_button)
        layout.addLayout(buttons_layout)

        dialog.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
        """)

        QTimer.singleShot(
            0,
            lambda: self._move_dialog_to_upper_position(dialog)
        )
        QTimer.singleShot(
            0,
            lambda: _position_custom_close_button(dialog)
        )

        return dialog.exec_() == QDialog.Accepted

    def init_scan_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        left_card = QFrame()
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title = QLabel("Add / Update Stock")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A; border: none;")

        back_btn = QPushButton("Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton { padding: 6px 14px; font-size: 13px; background-color: #F1F5F9; border-radius: 6px; font-weight: bold; color: #475569; border: 1px solid #E2E8F0; }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_btn.clicked.connect(self.clear_all_fields)
        back_btn.clicked.connect(self.on_back_to_menu)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        left_layout.addLayout(header_layout)

        left_layout.addSpacing(5)

        # ?? ???? ?????: ?????? ??? ????? (?????? ?? ??? ?????? ???? ??????)
        type_select_layout = QHBoxLayout()
        type_select_layout.addWidget(
            QLabel("Search by:", styleSheet="font-size: 14px; font-weight: bold; color: #475569;"))
        self.verification_mode_combo = QComboBox()
        self.verification_mode_combo.addItems(["Barcode", "Medicine Name"])
        self.verification_mode_combo.setStyleSheet(
            "padding: 6px; font-size: 14px; background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.verification_mode_combo.currentIndexChanged.connect(self.update_scan_placeholder)
        type_select_layout.addWidget(self.verification_mode_combo)
        type_select_layout.addStretch()
        left_layout.addLayout(type_select_layout)

        self.input_label = QLabel("Barcode:")
        self.input_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #475569;")
        left_layout.addWidget(self.input_label)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode or enter barcode...")
        self.barcode_input.setStyleSheet(
            "padding: 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; background-color: #F8FAFC;")
        self.barcode_input.focusInEvent = lambda event: self.handle_input_focus(self.barcode_input, event)
        self.barcode_input.returnPressed.connect(self.check_input_source)
        left_layout.addWidget(self.barcode_input)

        search_btn = QPushButton("Search")
        search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        search_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #0F766E; }
        """)
        search_btn.clicked.connect(self.check_input_source)
        left_layout.addWidget(search_btn)
        left_layout.addStretch()

        main_layout.addWidget(left_card, stretch=5)

        # ???????? ?????? ??????? ??????
        self.kb_card = QFrame()
        self.kb_card.setStyleSheet("background-color: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_layout = QVBoxLayout(self.kb_card)

        title_pad = QLabel("Keypad")
        title_pad.setStyleSheet("font-size: 12px; color: #64748B; font-weight: bold; padding-left: 2px;")
        kb_layout.addWidget(title_pad)

        num_grid = QVBoxLayout()
        num_grid.setSpacing(4)
        rows = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['Clear', '0', 'Back', 'Hide']]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(4)
            for k in row:
                btn = QPushButton(k)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(45)
                if k in ['Clear', 'Back', 'Hide']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; font-size: 13px; border-radius: 6px; border: none;")
                else:
                    btn.setStyleSheet(
                        "background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 13px; border-radius: 6px; border: 1px solid #CBD5E1;")
                btn.clicked.connect(lambda checked, key=k: self.handle_key_press(key))
                r_lay.addWidget(btn)
            num_grid.addLayout(r_lay)
        kb_layout.addLayout(num_grid)
        kb_layout.addStretch()

        main_layout.addWidget(self.kb_card, stretch=4)
        self.kb_card.hide()
        self.barcode_input.installEventFilter(self)

        self.internal_stack.addWidget(page)

    def update_scan_placeholder(self):
        """ ???? ????????? ??????? ????? ??? ???? ???????? (??? ?? ??????) """
        if self.verification_mode_combo.currentIndex() == 0:
            self.input_label.setText("Barcode:")
            self.barcode_input.setPlaceholderText("Scan barcode or enter barcode...")
            QTimer.singleShot(0, self.focus_stock_barcode_input)
        else:
            self.input_label.setText("Medicine Name:")
            self.barcode_input.setPlaceholderText("Type medicine name...")

    def _make_form_field(self, label_text, field_widget):
        box = QWidget()
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.setSpacing(3)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569;")
        box_layout.addWidget(label)

        field_widget.setMinimumHeight(34)
        field_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box_layout.addWidget(field_widget)
        return box

    def init_form_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")

        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        page_content = QWidget()
        page_content.setStyleSheet("background-color: #F8FAFC;")
        page_content.setMinimumHeight(560)

        main_layout = QHBoxLayout(page_content)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        form_card = QFrame()
        form_card.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; }
            QLabel { border: none; background-color: transparent; }
            QLineEdit, QComboBox, QSpinBox {
                padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px;
                font-size: 13px; background-color: #F8FAFC; color: #0F172A;
            }
        """)
        form_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(8)
        form_layout.setSizeConstraint(QLayout.SetDefaultConstraint)

        header_layout = QHBoxLayout()
        self.form_title = QLabel("Add / Update Stock")
        self.form_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0D9488; border: none;")
        header_layout.addWidget(self.form_title)
        header_layout.addStretch()

        back_form_btn = QPushButton("Back")
        back_form_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_form_btn.setMinimumHeight(32)
        back_form_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #475569; padding: 6px 14px; font-size: 13px; font-weight: bold; border-radius: 6px; border: 1px solid #E2E8F0; }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        back_form_btn.clicked.connect(self.go_back_to_stock_search)
        header_layout.addWidget(back_form_btn)

        form_layout.addLayout(header_layout)

        self.name_input = QLineEdit()
        self.name_input.focusInEvent = lambda event: self.handle_input_focus(self.name_input, event)

        self.category_input = QLineEdit()
        self.category_input.focusInEvent = lambda event: self.handle_input_focus(self.category_input, event)

        self.ingredient_input = QLineEdit()
        self.ingredient_input.focusInEvent = lambda event: self.handle_input_focus(self.ingredient_input, event)

        self.dosage_input = QLineEdit()
        self.dosage_input.focusInEvent = lambda event: self.handle_input_focus(self.dosage_input, event)

        self.batch_input = QLineEdit()
        self.batch_input.focusInEvent = lambda event: self.handle_input_focus(self.batch_input, event)

        self.expiry_month_input = QComboBox()
        self.expiry_month_input.addItems([f"{month:02d}" for month in range(1, 13)])
        self.expiry_month_input.setEditable(True)
        self.expiry_month_input.setInsertPolicy(QComboBox.NoInsert)
        self.expiry_month_input.lineEdit().setValidator(QIntValidator(1, 12, self))
        self.expiry_month_input.lineEdit().setMaxLength(2)
        self.expiry_month_input.lineEdit().setPlaceholderText("MM")
        self.expiry_month_input.setCurrentText(f"{QDate.currentDate().month():02d}")

        self.expiry_year_input = QComboBox()
        current_year = QDate.currentDate().year()
        self.expiry_year_input.addItems([str(year) for year in range(current_year, current_year + 21)])
        self.expiry_year_input.setEditable(True)
        self.expiry_year_input.setInsertPolicy(QComboBox.NoInsert)
        self.expiry_year_input.lineEdit().setValidator(QIntValidator(2000, 9999, self))
        self.expiry_year_input.lineEdit().setMaxLength(4)
        self.expiry_year_input.lineEdit().setPlaceholderText("YYYY")
        self.expiry_year_input.setCurrentText(str(current_year))

        self.expiry_selector = QWidget()
        expiry_selector_layout = QHBoxLayout(self.expiry_selector)
        expiry_selector_layout.setContentsMargins(0, 0, 0, 0)
        expiry_selector_layout.setSpacing(6)
        expiry_selector_layout.addWidget(self.expiry_month_input)
        expiry_selector_layout.addWidget(QLabel("/"))
        expiry_selector_layout.addWidget(self.expiry_year_input)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 5000)
        self.quantity_input.focusInEvent = lambda event: self.handle_input_focus(self.quantity_input, event)

        grid_holder = QWidget()
        grid = QGridLayout(grid_holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(self._make_form_field("Medicine Name", self.name_input), 0, 0)
        grid.addWidget(self._make_form_field("Category", self.category_input), 0, 1)
        grid.addWidget(self._make_form_field("Active Ingredient", self.ingredient_input), 1, 0)
        grid.addWidget(self._make_form_field("Dosage", self.dosage_input), 1, 1)
        grid.addWidget(self._make_form_field("Batch Number", self.batch_input), 2, 0)
        grid.addWidget(self._make_form_field("Expiry Month / Year", self.expiry_selector), 2, 1)
        grid.addWidget(self._make_form_field("Quantity", self.quantity_input), 3, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        form_layout.addWidget(grid_holder)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.submit_med_btn = QPushButton("Save")
        self.submit_med_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_med_btn.setMinimumHeight(38)
        self.submit_med_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; padding: 8px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #0F766E; }
        """)
        self.submit_med_btn.clicked.connect(self.save_medication)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #F1F5F9; color: #475569; padding: 8px; font-size: 13px; font-weight: 600; border-radius: 6px; border: 1px solid #E2E8F0; }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        cancel_btn.clicked.connect(self.go_back_to_stock_search)

        btn_layout.addWidget(self.submit_med_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()

        form_card.setMinimumWidth(520)
        form_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(form_card, stretch=7)

        self.kb_full_card = QFrame()
        self.kb_full_card.setStyleSheet("background-color: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0;")
        kb_full_card_layout = QVBoxLayout(self.kb_full_card)
        kb_full_card_layout.setContentsMargins(6, 6, 6, 6)
        kb_full_card_layout.setSpacing(4)

        title_kb2 = QLabel("Keyboard")
        title_kb2.setStyleSheet("font-size: 12px; color: #64748B; font-weight: bold; border: none; margin-bottom: 2px;")
        kb_full_card_layout.addWidget(title_kb2)

        keyboard_widget = QWidget()
        keyboard_lay = QVBoxLayout(keyboard_widget)
        keyboard_lay.setContentsMargins(0, 0, 0, 0)
        keyboard_lay.setSpacing(4)

        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ' ', 'Clear', 'Back', 'Hide']
        ]
        for row in rows:
            r_lay = QHBoxLayout()
            r_lay.setSpacing(3)
            for key in row:
                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(34)

                if key in ['Clear', 'Back', 'Hide']:
                    btn.setStyleSheet(
                        "background-color: #CBD5E1; color: #1E293B; font-weight: bold; font-size: 11px; border-radius: 6px; border: none;")
                elif key == ' ':
                    btn.setText("Space")
                    btn.setStyleSheet(
                        "background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 11px; border: 1px solid #CBD5E1; border-radius: 6px; min-width: 40px;")
                else:
                    btn.setStyleSheet(
                        "background-color: #FFFFFF; color: #1E293B; font-weight: bold; font-size: 11px; border: 1px solid #CBD5E1; border-radius: 6px;")
                btn.clicked.connect(lambda checked, k=key: self.handle_key_press(k))
                r_lay.addWidget(btn)
            keyboard_lay.addLayout(r_lay)
        kb_full_card_layout.addWidget(keyboard_widget)
        kb_full_card_layout.addStretch()

        self.kb_full_scroll = self._make_scroll_area(self.kb_full_card)
        self.kb_full_scroll.setMaximumWidth(470)
        self.kb_full_scroll.setMinimumWidth(360)
        self.kb_full_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        main_layout.addWidget(self.kb_full_scroll, stretch=5)
        self.kb_full_scroll.hide()

        self.name_input.installEventFilter(self)
        self.category_input.installEventFilter(self)
        self.ingredient_input.installEventFilter(self)
        self.dosage_input.installEventFilter(self)
        self.batch_input.installEventFilter(self)
        self.quantity_input.installEventFilter(self)

        page_scroll = self._make_scroll_area(page_content)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer_layout.addWidget(page_scroll)

        self.internal_stack.addWidget(page)

    def go_back_to_stock_search(self):
        if hasattr(self, 'kb_full_card'):
            self.kb_full_card.hide()
        if hasattr(self, 'kb_full_scroll'):
            self.kb_full_scroll.hide()
        self.internal_stack.setCurrentIndex(0)
        QTimer.singleShot(150, self.focus_stock_barcode_input)

    def handle_input_focus(self, input_field, event):
        for box in [self.barcode_input, self.name_input, self.category_input, self.ingredient_input, self.dosage_input,
                    self.batch_input]:
            box.setStyleSheet(
                "padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; background-color: #F8FAFC; color: #1E293B;")
        combo_style = (
            "QComboBox { padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; "
            "font-size: 13px; background-color: #F8FAFC; color: #0F172A; }"
        )
        self.expiry_month_input.setStyleSheet(combo_style)
        self.expiry_year_input.setStyleSheet(combo_style)
        self.quantity_input.setStyleSheet(
            "padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; background-color: #F8FAFC; color: #0F172A;")

        self.current_focused_input = input_field

        if event:
            if isinstance(input_field, QLineEdit):
                super(QLineEdit, input_field).focusInEvent(event)
            elif isinstance(input_field, QSpinBox):
                super(QSpinBox, input_field).focusInEvent(event)

        input_field.setStyleSheet(
            "padding: 6px; border: 2px solid #0D9488; border-radius: 6px; font-size: 13px; background-color: #F0FDFA; color: #0F172A; font-weight: bold;")

    def eventFilter(self, obj, event):
        # The kiosk now uses the physical barcode scanner and normal text fields.
        # The custom on-screen keyboard/keypad is disabled so it never pops up.
        return super().eventFilter(obj, event)

    def handle_key_press(self, key):
        if not self.current_focused_input: return

        if key in ['??', 'Hide']:
            if self.internal_stack.currentIndex() == 0:
                self.kb_card.hide()
            else:
                self.kb_full_card.hide()
                if hasattr(self, 'kb_full_scroll'): self.kb_full_scroll.hide()
            return

        if isinstance(self.current_focused_input, QSpinBox):
            current_val = str(self.current_focused_input.value())
            if key in ['?', 'Back']:
                new_val = current_val[:-1]
                self.current_focused_input.setValue(int(new_val) if new_val and new_val != '-' else 1)
            elif key == 'Clear':
                self.current_focused_input.setValue(1)
            elif key.isdigit():
                if current_val == "1" and key != "0":
                    self.current_focused_input.setValue(int(key))
                else:
                    self.current_focused_input.setValue(int(current_val + key))

        elif isinstance(self.current_focused_input, QLineEdit):
            current_text = self.current_focused_input.text()
            if key in ['?', 'Back']:
                self.current_focused_input.setText(current_text[:-1])
            elif key == 'Clear':
                self.current_focused_input.clear()
            else:
                self.current_focused_input.setText(current_text + key)

        self.current_focused_input.setFocus(Qt.OtherFocusReason)

    def check_input_source(self):
        """ ???? ????? ????? ??? ?? ???? ???????? ?? ?? ???? ??? ?????? ?????? """
        search_val = self.barcode_input.text().strip()
        if not search_val:
            show_safe_message(self, QMessageBox.Warning, "Error", "Please enter search information first.")
            return

        # ??? ?????? ????? ?????????
        if self.verification_mode_combo.currentIndex() == 0:
            self.check_barcode(explicit_barcode=search_val)
        else:
            # ??? ?????? ????? ???? ?????? ???? ???? ???? ??????
            self.check_by_medicine_name(med_name=search_val)

    def check_by_medicine_name(self, med_name):
        """
        Find every stock record that belongs to the exact medicine name.

        The search is exact but ignores letter case and repeated/outer spaces.
        Records are included regardless of whether they were originally added
        through medicine-name search or barcode search.
        """
        try:
            self.kb_card.hide()

            def normalize_name(value):
                return " ".join(str(value or "").strip().lower().split())

            requested_name = normalize_name(med_name)

            # Read all stock rows, then compare the actual Medicine Name field.
            # This guarantees that barcode-created batches are included too.
            all_records = airtable_api.stock_table.all()

            records = []
            for record in all_records:
                fields = (
                    record.fields
                    if hasattr(record, "fields")
                    else record.get("fields", {})
                )

                stored_name = normalize_name(fields.get("Medicine Name", ""))

                if stored_name == requested_name:
                    records.append(record)

            existing_batches = []
            for r in records:
                fields = r.fields if hasattr(r, 'fields') else r.get('fields', {})
                existing_batches.append({
                    "id": r.id if hasattr(r, 'id') else r.get('id'),
                    "medicine_name": fields.get("Medicine Name", "Unknown"),
                    "expiry_date": fields.get("Expiry Date", ""),
                    "current_quantity": (
                        fields.get("Current Pills Count")
                        or fields.get("Quantity")
                        or 0
                    ),
                    "batch_number": (
                        fields.get("A Batch")
                        or fields.get("Batch Number")
                        or "N/A"
                    ),
                    "barcode": self.extract_barcode_from_fields(fields)
                })

            if existing_batches:
                # Keep the real barcode of the existing medicine even though
                # the user searched by medicine name.
                self.resolved_barcode = next(
                    (
                        batch.get("barcode")
                        for batch in existing_batches
                        if batch.get("barcode")
                    ),
                    None
                )

                dialog = BatchSelectionDialog(existing_batches, self)
                if dialog.exec_() == QDialog.Accepted:
                    if dialog.action_type == "edit":
                        selected = dialog.selected_batch
                        self.existing_record_id = selected["id"]

                        if selected.get("barcode"):
                            self.resolved_barcode = selected["barcode"]

                        record = airtable_api.stock_table.get(self.existing_record_id)
                        fields = record.get('fields', {})

                        self.name_input.setText(str(fields.get("Medicine Name", "")))
                        self.name_input.setEnabled(True)
                        self.category_input.setText(str(fields.get("Category", "")))
                        self.category_input.setEnabled(True)
                        self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                        self.dosage_input.setText(str(fields.get("Dosage", "")))
                        self.dosage_input.setEnabled(True)

                        self.batch_input.setText(str(selected.get("batch_number", "")))
                        self.batch_input.setEnabled(True)
                        self.set_expiry_from_airtable(selected.get("expiry_date", ""))
                        self.quantity_input.setValue(int(selected.get("current_quantity", 1)))

                        self.form_title.setText("Edit")
                        self.submit_med_btn.setText("Update")
                        self.internal_stack.setCurrentIndex(1)
                        self.handle_input_focus(self.quantity_input, None)

                    elif dialog.action_type == "new":
                        self.existing_record_id = None
                        first_batch = existing_batches[0]

                        if first_batch.get("barcode"):
                            self.resolved_barcode = first_batch["barcode"]

                        self.name_input.setText(str(first_batch.get("medicine_name", "")))
                        self.name_input.setEnabled(False)

                        record = airtable_api.stock_table.get(first_batch["id"])
                        fields = record.get('fields', {})

                        self.category_input.setText(str(fields.get("Category", "")))
                        self.category_input.setEnabled(False)
                        self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                        self.ingredient_input.setEnabled(False)
                        self.dosage_input.setText(str(fields.get("Dosage", "")))
                        self.dosage_input.setEnabled(False)

                        self.batch_input.clear()
                        self.batch_input.setEnabled(True)
                        self.reset_expiry_selection()
                        self.quantity_input.setValue(1)

                        self.form_title.setText("Add New Batch")
                        self.submit_med_btn.setText("Save")
                        self.internal_stack.setCurrentIndex(1)
                        self.handle_input_focus(self.batch_input, None)
            else:
                # This is a completely new medicine, so no existing barcode
                # can be recovered from Airtable.
                self.resolved_barcode = None
                self.existing_record_id = None
                self.name_input.setText(med_name)
                self.name_input.setEnabled(True)
                self.category_input.clear()
                self.category_input.setEnabled(True)
                self.ingredient_input.clear()
                self.ingredient_input.setEnabled(True)
                self.dosage_input.clear()
                self.dosage_input.setEnabled(True)
                self.batch_input.clear()
                self.batch_input.setEnabled(True)
                self.reset_expiry_selection()
                self.quantity_input.setValue(1)

                self.form_title.setText("Add New Medicine")
                self.submit_med_btn.setText("Save")
                self.internal_stack.setCurrentIndex(1)
                self.handle_input_focus(self.category_input, None)

        except Exception as e:
            print(f"Error checking medicine name: {e}")

    def check_barcode(self, explicit_barcode=None):
        barcode = explicit_barcode or self.barcode_input.text().strip()
        self.resolved_barcode = barcode if barcode else None

        try:
            self.kb_card.hide()

            def normalize_name(value):
                return " ".join(str(value or "").strip().lower().split())

            # First resolve the scanned barcode to its medicine name.
            barcode_records = airtable_api.get_all_medications_by_barcode(barcode)

            matched_name = ""
            for record in barcode_records:
                fields = (
                    record.fields
                    if hasattr(record, "fields")
                    else record.get("fields", {})
                )
                candidate_name = fields.get("Medicine Name", "")
                if str(candidate_name or "").strip():
                    matched_name = str(candidate_name).strip()
                    break

            # Then load every stock row with that exact medicine name,
            # including rows created previously by name with NO_BARCODE.
            if matched_name:
                requested_name = normalize_name(matched_name)
                raw_records = []

                for record in airtable_api.stock_table.all():
                    fields = (
                        record.fields
                        if hasattr(record, "fields")
                        else record.get("fields", {})
                    )

                    if normalize_name(fields.get("Medicine Name", "")) == requested_name:
                        raw_records.append(record)
            else:
                raw_records = barcode_records

            existing_batches = []
            for record in raw_records:
                fields = (
                    record.fields
                    if hasattr(record, "fields")
                    else record.get("fields", {})
                )
                record_id = (
                    record.id
                    if hasattr(record, "id")
                    else record.get("id")
                )

                existing_batches.append({
                    "id": record_id,
                    "medicine_name": fields.get("Medicine Name", "Unknown"),
                    "expiry_date": fields.get("Expiry Date", ""),
                    "current_quantity": (
                        fields.get("Current Pills Count")
                        or fields.get("Quantity")
                        or 0
                    ),
                    "batch_number": (
                        fields.get("A Batch")
                        or fields.get("Batch Number")
                        or "N/A"
                    ),
                    "barcode": (
                        self.extract_barcode_from_fields(fields)
                        or barcode
                    )
                })

            if existing_batches:
                dialog = BatchSelectionDialog(existing_batches, self)
                if dialog.exec_() == QDialog.Accepted:
                    if dialog.action_type == "edit":
                        selected = dialog.selected_batch
                        self.existing_record_id = selected["id"]
                        self.resolved_barcode = selected.get("barcode") or barcode

                        record = airtable_api.stock_table.get(self.existing_record_id)
                        fields = record.get('fields', {})

                        self.name_input.setText(str(fields.get("Medicine Name", "")))
                        self.name_input.setEnabled(True)
                        self.category_input.setText(str(fields.get("Category", "")))
                        self.category_input.setEnabled(True)
                        self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                        self.dosage_input.setText(str(fields.get("Dosage", "")))
                        self.dosage_input.setEnabled(True)

                        self.batch_input.setText(str(selected.get("batch_number", "")))
                        self.batch_input.setEnabled(True)
                        self.set_expiry_from_airtable(selected.get("expiry_date", ""))
                        self.quantity_input.setValue(int(selected.get("current_quantity", 1)))

                        self.form_title.setText("Edit Batch")
                        self.submit_med_btn.setText("Update Batch")
                        self.internal_stack.setCurrentIndex(1)
                        self.handle_input_focus(self.quantity_input, None)

                    elif dialog.action_type == "new":
                        self.existing_record_id = None
                        first_batch = existing_batches[0]
                        self.resolved_barcode = barcode

                        self.name_input.setText(str(first_batch.get("medicine_name", "")))
                        self.name_input.setEnabled(False)

                        record = airtable_api.stock_table.get(first_batch["id"])
                        fields = record.get('fields', {})

                        self.category_input.setText(str(fields.get("Category", "")))
                        self.category_input.setEnabled(False)
                        self.ingredient_input.setText(str(fields.get("Active Ingredient", "")))
                        self.ingredient_input.setEnabled(False)
                        self.dosage_input.setText(str(fields.get("Dosage", "")))
                        self.dosage_input.setEnabled(False)

                        self.batch_input.clear()
                        self.batch_input.setEnabled(True)
                        self.reset_expiry_selection()
                        self.quantity_input.setValue(1)

                        self.form_title.setText("Add New Batch")
                        self.submit_med_btn.setText("Save")
                        self.internal_stack.setCurrentIndex(1)
                        self.handle_input_focus(self.batch_input, None)
            else:
                self.existing_record_id = None
                self.resolved_barcode = barcode
                self.name_input.clear()
                self.name_input.setEnabled(True)
                self.category_input.clear()
                self.category_input.setEnabled(True)
                self.ingredient_input.clear()
                self.ingredient_input.setEnabled(True)
                self.dosage_input.clear()
                self.dosage_input.setEnabled(True)
                self.batch_input.clear()
                self.batch_input.setEnabled(True)
                self.reset_expiry_selection()
                self.quantity_input.setValue(1)

                self.form_title.setText("Add New Medicine")
                self.submit_med_btn.setText("Save")
                self.internal_stack.setCurrentIndex(1)
                self.handle_input_focus(self.name_input, None)

        except Exception as e:
            print(f"Error during check barcode: {e}")

    def reset_expiry_selection(self):
        today = QDate.currentDate()
        self.expiry_month_input.setCurrentText(f"{today.month():02d}")
        self.expiry_year_input.setCurrentText(str(today.year()))

    def set_expiry_from_airtable(self, expiry_value):
        expiry_date = QDate.fromString(str(expiry_value), "yyyy-MM-dd")
        if not expiry_date.isValid():
            self.reset_expiry_selection()
            return

        self.expiry_month_input.setCurrentText(f"{expiry_date.month():02d}")
        self.expiry_year_input.setCurrentText(str(expiry_date.year()))

    def save_medication(self):
        # Prefer the barcode resolved from an existing medicine record.
        # Fall back to the scanned value only when creating a truly new item.
        barcode = (self.resolved_barcode or "").strip()

        if not barcode and self.verification_mode_combo.currentIndex() == 0:
            barcode = self.barcode_input.text().strip()

        if not barcode:
            barcode = "NO_BARCODE"
        name = self.name_input.text().strip()
        ingredient = self.ingredient_input.text().strip()
        cat = self.category_input.text().strip()
        dosage = self.dosage_input.text().strip()
        batch = self.batch_input.text().strip()

        month_text = self.expiry_month_input.currentText().strip()
        year_text = self.expiry_year_input.currentText().strip()

        try:
            expiry_month = int(month_text)
            expiry_year = int(year_text)
        except ValueError:
            show_safe_message(
                self, QMessageBox.Warning, "Input Error",
                "Please enter a valid expiry month and year."
            )
            return

        if expiry_month < 1 or expiry_month > 12:
            show_safe_message(
                self, QMessageBox.Warning, "Input Error",
                "Expiry month must be between 1 and 12."
            )
            return

        if expiry_year < 2000 or expiry_year > 9999:
            show_safe_message(
                self, QMessageBox.Warning, "Input Error",
                "Please enter a valid four-digit expiry year."
            )
            return

        expiry_last_day = monthrange(expiry_year, expiry_month)[1]
        clean_expiry_str = QDate(expiry_year, expiry_month, expiry_last_day).toString("yyyy-MM-dd")
        qty = self.quantity_input.value()

        if not name or not batch:
            show_safe_message(self, QMessageBox.Warning, "Input Error", "Medicine name and batch number are required.")
            return

        selected_date = datetime.strptime(clean_expiry_str, "%Y-%m-%d").date()
        if selected_date < datetime.now().date():
            show_safe_message(self, QMessageBox.Critical, "Expired Medication", "Cannot add expired medicine.")
            return

        confirm_msg = (
            "Please confirm:\n\n"
            f"Medicine: {name}\n"
            f"Category: {cat or '-'}\n"
            f"Expiry: {expiry_month:02d}/{expiry_year}\n"
            f"Quantity: {qty} pills\n\n"
            "Save this stock change?"
        )

        if not self.ask_upper_confirmation("Confirm Stock", confirm_msg):
            return

        try:
            if self.existing_record_id:
                # Update the exact Airtable stock record that was selected.
                # The previous helper used the wrong Airtable field name
                # ("A Category"), so Airtable rejected the entire update.
                fields_to_update = {
                    "Medicine Name": str(name),
                    "Barcode": str(barcode),
                    "Active Ingredient": str(ingredient),
                    "Dosage": str(dosage),
                    "Expiry Date": str(clean_expiry_str),
                    "Current Pills Count": int(qty),
                    "A Batch": str(batch),
                    "Category": str(cat),
                }

                record = airtable_api.stock_table.update(
                    self.existing_record_id,
                    fields_to_update,
                    typecast=True
                )

                if not record:
                    raise RuntimeError(
                        "Airtable did not return the updated medication record."
                    )

                print(
                    "MedicationManagementPage: updated Airtable record "
                    f"{self.existing_record_id}"
                )

                # No extra success popup: confirmation is the only dialog before saving.
                self.clear_all_fields()
            else:
                record = airtable_api.add_new_medication(
                    name, barcode, ingredient, dosage, clean_expiry_str, qty, qty, batch, cat,
                    user_record_id=self.current_user_record_id
                )
                if record:
                    # No extra success popup: confirmation is the only dialog before saving.
                    self.clear_all_fields()
        except Exception as e:
            show_safe_message(self, QMessageBox.Critical, "Save Error", f"Save failed:\n{str(e)}")

    def json(self):
        return {}

    def clear_all_fields(self):
        self.barcode_input.clear()
        self.name_input.clear()
        self.name_input.setEnabled(True)
        self.ingredient_input.clear()
        self.ingredient_input.setEnabled(True)
        self.category_input.clear()
        self.category_input.setEnabled(True)
        self.dosage_input.clear()
        self.dosage_input.setEnabled(True)
        self.batch_input.clear()
        self.batch_input.setEnabled(True)
        self.reset_expiry_selection()
        self.quantity_input.setValue(1)
        self.existing_record_id = None
        self.resolved_barcode = None
        self.verification_mode_combo.setCurrentIndex(0)
        self.internal_stack.setCurrentIndex(0)

        if hasattr(self, 'kb_card'): self.kb_card.hide()
        if hasattr(self, 'kb_full_card'): self.kb_full_card.hide()
        if hasattr(self, 'kb_full_scroll'): self.kb_full_scroll.hide()

        self.handle_input_focus(self.barcode_input, None)
        QTimer.singleShot(150, self.focus_stock_barcode_input)