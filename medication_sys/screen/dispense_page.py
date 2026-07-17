import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QComboBox, QHeaderView, QCheckBox, QInputDialog,
    QScrollArea, QSizePolicy, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QCursor
import airtable_api


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


class DispenseMedicationPage(QWidget):
    """
    Medication dispensing screen.
    Supports offline stock lookup, live search, batch selection, and FIFO dispensing.
    """

    def __init__(self, parent=None, on_back_to_menu=None):
        super().__init__(parent)
        self.on_back_to_menu = on_back_to_menu
        self.user_role = "User"
        self.user_full_name = "System User"
        self.scanned_barcode = ""
        self.selected_medicine_name = ""
        self.loaded_batches = []
        self.all_cached_inventory = []

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.internal_stack = QStackedWidget(self)
        self.internal_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.init_scan_screen()  # Index 0
        self.init_selection_screen()  # Index 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.internal_stack)

        self.internal_stack.setCurrentIndex(0)

        # Preload cloud database catalog directly upon widget instance initialization
        self.preload_inventory_cache()

        # Scanner is a USB keyboard, so keep the barcode input ready by default.
        QTimer.singleShot(150, self.focus_barcode_scanner)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self.focus_barcode_scanner)

    def focus_barcode_scanner(self):
        """Prepare the screen for immediate barcode scanning without a click."""
        try:
            self.internal_stack.setCurrentIndex(0)
            if self.search_type_combo.currentText() != "Barcode":
                self.search_type_combo.setCurrentText("Barcode")
            self.search_input.setFocus(Qt.OtherFocusReason)
            self.search_input.selectAll()
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
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(message)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        make_dialog_kiosk_safe(box)
        QTimer.singleShot(0, lambda: self._move_dialog_to_upper_position(box))
        return box.exec_() == QMessageBox.Yes

    def _clean_session_value(self, value):
        if value is None:
            return ""
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value).strip()
        if text.lower() in ("none", "null", "nan"):
            return ""
        return text

    def set_user_session(self, role, full_name, username=None):
        self.user_role = self._clean_session_value(role).lower() or "user"

        # Full name is preferred for Dispensed_History -> Action By User.
        # Username is only a fallback so we never write the generic System User.
        resolved_name = self._clean_session_value(full_name) or self._clean_session_value(username)
        if resolved_name:
            self.user_full_name = resolved_name

        self.preload_inventory_cache()

    def get_action_by_user_name(self):
        """Return the name that should be written to Dispensed_History / Action By User."""
        name = self._clean_session_value(self.user_full_name)
        if not name or name == "System User":
            return "Staff"
        return name

    def _clean_barcode_value(self, value):
        """Return a real barcode string and ignore Airtable record IDs/placeholders."""
        if value is None:
            return ""

        values = value if isinstance(value, list) else [value]
        for current in values:
            if isinstance(current, dict):
                current = current.get("text") or current.get("value") or current.get("name") or ""
            text = str(current).strip()
            low = text.lower()

            # Ignore lookup headers, empty values, and Airtable linked-record IDs like recXXXXXXXX.
            if low in ("", "none", "null", "nan", "barcode", "no_barcode", "n/a"):
                continue
            if low.startswith("rec") and len(text) >= 10:
                continue
            return text

        return ""

    def _extract_real_barcode_from_fields(self, fields):
        """Extract the actual scanner barcode from all supported Airtable field names."""
        fields = fields or {}
        candidates = [
            fields.get("Search key (auto 12)"),
            fields.get("Barcode (from Barcode)"),
            fields.get("Barcode lookup"),
            fields.get("Barcode"),
        ]
        for candidate in candidates:
            clean = self._clean_barcode_value(candidate)
            if clean:
                return clean
        return ""

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
                    # Use the real scanner barcode, not Airtable linked-record IDs.
                    # In this base the real value may be in "Barcode (from Barcode)".
                    clean_b = self._extract_real_barcode_from_fields(fields)

                    self.all_cached_inventory.append({
                        "id": r.id if hasattr(r, 'id') else r.get('id'),
                        "name": airtable_api.safe_extract(fields.get("Medicine Name"), str),
                        "barcode": clean_b,
                        "ingredient": airtable_api.safe_extract(fields.get("Active Ingredient"), str),
                        "category": airtable_api.safe_extract(fields.get("Category"), str) or airtable_api.safe_extract(fields.get("A Category"), str) or "N/A",
                        "dosage": airtable_api.safe_extract(fields.get("Dosage"), str) or airtable_api.safe_extract(
                            fields.get("Category"), str) or "N/A",
                        "qty": qty,
                        "batch": airtable_api.safe_extract(fields.get("A Batch"), str) or airtable_api.safe_extract(
                            fields.get("Batch Number"), str) or "N/A",
                        "expiry": airtable_api.safe_extract(fields.get("Expiry Date") or fields.get("Expiry"), str)
                    })

            #  Populate the main summary master table immediately after completing the fetch loop
            self.run_live_filter()
        except Exception as e:
            print(f"WARNING Stock cache bypass log: {e}")

    def _make_scroll_area(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 35px; border-radius: 7px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        scroll.setWidget(widget)
        return scroll

    # =====================================================================
    #  SCREEN 0: Live Search & Scanner Entry Layout (Large Readable Text)
    # =====================================================================
    def init_scan_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        # Left side: compact search controls for landscape kiosk view.
        left_card = QFrame()
        left_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_layout.setAlignment(Qt.AlignTop)

        header_layout = QHBoxLayout()
        title = QLabel("Dispense")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4F46E5; border: none;")

        back_btn = QPushButton("Menu")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setMinimumHeight(34)
        back_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px; font-size: 13px; background-color: #F1F5F9; border-radius: 6px;
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

        lbl = QLabel("Search")
        lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        left_layout.addWidget(lbl)

        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Barcode", "Medicine Name", "Category", "Active Ingredient", "Batch"])
        self.search_type_combo.setMinimumHeight(34)
        self.search_type_combo.setStyleSheet("""
            QComboBox { padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px; background-color: #FFFFFF; color: #1E293B; }
        """)
        self.search_type_combo.currentIndexChanged.connect(self.update_search_placeholder)
        self.search_type_combo.currentIndexChanged.connect(self.run_live_filter)
        left_layout.addWidget(self.search_type_combo)

        input_lbl = QLabel("Scan or type")
        input_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        left_layout.addWidget(input_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type barcode...")
        self.search_input.setFocusPolicy(Qt.StrongFocus)
        self.search_input.setMinimumHeight(38)
        self.search_input.setStyleSheet(
            "padding: 8px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px;")
        self.search_input.textChanged.connect(self.run_live_filter)
        self.search_input.returnPressed.connect(self.handle_scanner_return_pressed)
        left_layout.addWidget(self.search_input)

        hint = QLabel("Choose a search type, then select a medicine from the list.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #64748B; border: none;")
        left_layout.addWidget(hint)
        left_layout.addStretch()

        # Right side: medicine list uses the wide part of the screen.
        list_card = QFrame()
        list_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(8)
        list_layout.setAlignment(Qt.AlignTop)

        list_title = QLabel("Medicines")
        list_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A; border: none;")
        list_layout.addWidget(list_title)

        self.live_matches_list = QTableWidget()
        self.live_matches_list.setColumnCount(3)
        self.live_matches_list.setHorizontalHeaderLabels(["Medicine", "Category", "Barcode"])
        self.live_matches_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.live_matches_list.setEditTriggers(QTableWidget.NoEditTriggers)

        self.live_matches_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.live_matches_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.live_matches_list.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.live_matches_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.live_matches_list.setMinimumHeight(260)

        self.live_matches_list.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; background: #F8FAFC; font-size: 13px; }
            QHeaderView::section { background-color: #F1F5F9; font-weight: bold; color: #475569; border: none; padding: 6px; font-size: 13px; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 35px; border-radius: 7px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        self.live_matches_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.live_matches_list.verticalHeader().setDefaultSectionSize(32)
        self.live_matches_list.itemClicked.connect(self.handle_table_row_selection)
        self.live_matches_list.itemActivated.connect(self.handle_table_row_selection)
        list_layout.addWidget(self.live_matches_list, stretch=1)

        main_layout.addWidget(self._make_scroll_area(left_card), stretch=2)
        main_layout.addWidget(self._make_scroll_area(list_card), stretch=6)
        self.internal_stack.addWidget(page)

    # =====================================================================
    #  SCREEN 1: Grid Table Selection Board (Large Readable Text)
    # =====================================================================
    def init_selection_screen(self):
        page = QWidget()
        page.setStyleSheet("background-color: #F8FAFC;")
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left side: selected medicine and batch list.
        batch_card = QFrame()
        batch_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        batch_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        batch_layout = QVBoxLayout(batch_card)
        batch_layout.setContentsMargins(12, 12, 12, 12)
        batch_layout.setSpacing(8)
        batch_layout.setAlignment(Qt.AlignTop)

        self.med_name_title = QLabel("Medicine: Loading...")
        self.med_name_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4F46E5;")
        self.med_name_title.setWordWrap(True)
        batch_layout.addWidget(self.med_name_title)

        self.total_stock_lbl = QLabel("Available: --")
        self.total_stock_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")
        batch_layout.addWidget(self.total_stock_lbl)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(5)
        self.batch_table.setHorizontalHeaderLabels(["Select", "Batch", "Expiry", "Qty", "Status"])
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.batch_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.batch_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.batch_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.batch_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.batch_table.setMinimumHeight(260)

        self.batch_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E2E8F0; border-radius: 8px; font-size: 13px; background-color: #FFFFFF; }
            QHeaderView::section { background-color: #F8FAFC; font-weight: bold; padding: 6px; color: #475569; font-size: 13px; }
            QScrollBar:vertical { border: none; background: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; }
            QScrollBar::handle:vertical { background: #CBD5E1; min-height: 35px; border-radius: 7px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
        """)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.batch_table.verticalHeader().setDefaultSectionSize(32)
        batch_layout.addWidget(self.batch_table, stretch=1)

        # Right side: quantity and action buttons. This fits landscape screens better.
        action_card = QFrame()
        action_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        action_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0;")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(12, 12, 12, 12)
        action_layout.setSpacing(8)
        action_layout.setAlignment(Qt.AlignTop)

        qty_label = QLabel("Quantity")
        qty_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #475569;")
        action_layout.addWidget(qty_label)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter quantity")
        self.quantity_input.setMinimumHeight(40)
        self.quantity_input.setStyleSheet(
            "padding: 8px; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 6px; background-color: #F8FAFC;")
        action_layout.addWidget(self.quantity_input)

        hint = QLabel("If no box is selected, the system uses the earliest expiry first.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #64748B;")
        action_layout.addWidget(hint)

        self.dispense_btn = QPushButton("Dispense")
        self.dispense_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.dispense_btn.setMinimumHeight(42)
        self.dispense_btn.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; padding: 9px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.dispense_btn.clicked.connect(self.execute_smart_dispense)
        action_layout.addWidget(self.dispense_btn)

        another_btn = QPushButton("Scan another")
        another_btn.setCursor(QCursor(Qt.PointingHandCursor))
        another_btn.setMinimumHeight(38)
        another_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 8px; font-size: 13px; font-weight: bold; border-radius: 6px; border: 1px solid #E2E8F0;")
        another_btn.clicked.connect(self.focus_barcode_scanner)
        action_layout.addWidget(another_btn)

        finish_btn = QPushButton("Menu")
        finish_btn.setCursor(QCursor(Qt.PointingHandCursor))
        finish_btn.setMinimumHeight(38)
        finish_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; padding: 8px; font-size: 13px; font-weight: bold; border-radius: 6px; border: none;")
        finish_btn.clicked.connect(self.clear_page)
        finish_btn.clicked.connect(self.on_back_to_menu)
        action_layout.addWidget(finish_btn)
        action_layout.addStretch()

        main_layout.addWidget(self._make_scroll_area(batch_card), stretch=6)
        main_layout.addWidget(self._make_scroll_area(action_card), stretch=2)
        self.internal_stack.addWidget(page)

    # =====================================================================
    #  INTERACTIVE INTERFACE LOGIC & DATA PARSING
    # =====================================================================
    def handle_input_focus(self, input_field, event):
        for box in [self.search_input, self.quantity_input]:
            box.setStyleSheet(
                "padding: 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; background-color: #F8FAFC; color: #1E293B;")
        if event: super(QLineEdit, input_field).focusInEvent(event)
        input_field.setStyleSheet(
            "padding: 10px; border: 2px solid #6366F1; border-radius: 6px; font-size: 14px; background-color: #F5F3FF; color: #0F172A; font-weight: bold;")

    def update_search_placeholder(self):
        search_type = self.search_type_combo.currentText()
        if search_type == "Barcode":
            self.search_input.setPlaceholderText("Type barcode...")
        elif search_type == "Medicine Name":
            self.search_input.setPlaceholderText("Type medicine name...")
        elif search_type == "Category":
            self.search_input.setPlaceholderText("Type category...")
        elif search_type == "Active Ingredient":
            self.search_input.setPlaceholderText("Type active ingredient...")
        elif search_type == "Batch":
            self.search_input.setPlaceholderText("Type batch number...")
        QTimer.singleShot(0, lambda: self.search_input.setFocus(Qt.OtherFocusReason))

    def run_live_filter(self):
        """ Fully optimized filter matching text dynamically with default master state recovery """
        search_text = self.search_input.text().strip().lower()
        search_type = self.search_type_combo.currentText()
        self.live_matches_list.setRowCount(0)

        if not self.all_cached_inventory: return

        matched_items = []
        # Offline-safe logic.
        if not search_text:
            matched_items = self.all_cached_inventory
        else:
            for med in self.all_cached_inventory:
                values_to_check = []
                if search_type == "Barcode":
                    values_to_check = [med.get("barcode", "")]
                elif search_type == "Medicine Name":
                    values_to_check = [med.get("name", "")]
                elif search_type == "Category":
                    values_to_check = [med.get("category", "")]
                elif search_type == "Active Ingredient":
                    values_to_check = [med.get("ingredient", "")]
                elif search_type == "Batch":
                    values_to_check = [med.get("batch", "")]

                if any(search_text in str(v).lower() for v in values_to_check):
                    matched_items.append(med)

        # Show each medicine only once on the main dispense screen.
        # If some batches have no barcode and another batch of the same
        # medicine has a real barcode, prefer showing the real barcode.
        grouped_by_name = {}

        for med in matched_items:
            medicine_name = str(med.get("name", "")).strip()
            if not medicine_name:
                continue

            name_key = medicine_name.lower()
            clean_barcode = self._clean_barcode_value(med.get("barcode"))

            if name_key not in grouped_by_name:
                grouped_by_name[name_key] = {
                    "name": medicine_name,
                    "category": med.get("category", "N/A"),
                    "barcode": clean_barcode
                }
            else:
                # Replace an empty/N/A barcode with a real one when available.
                if not grouped_by_name[name_key]["barcode"] and clean_barcode:
                    grouped_by_name[name_key]["barcode"] = clean_barcode

                # Keep a useful category if the first row had no category.
                current_category = str(
                    grouped_by_name[name_key].get("category", "")
                ).strip()
                new_category = str(med.get("category", "")).strip()

                if current_category in ("", "N/A") and new_category:
                    grouped_by_name[name_key]["category"] = new_category

        self.live_matches_list.setRowCount(0)

        for row_idx, med in enumerate(grouped_by_name.values()):
            clean_barcode = med.get("barcode", "")
            display_barcode = clean_barcode or "N/A"

            self.live_matches_list.insertRow(row_idx)

            name_item = QTableWidgetItem(med["name"])
            category_item = QTableWidgetItem(
                str(med.get("category", "N/A"))
            )
            barcode_item = QTableWidgetItem(str(display_barcode))

            name_item.setData(Qt.UserRole, clean_barcode)

            self.live_matches_list.setItem(row_idx, 0, name_item)
            self.live_matches_list.setItem(row_idx, 1, category_item)
            self.live_matches_list.setItem(row_idx, 2, barcode_item)

    def handle_scanner_return_pressed(self):
        if self.live_matches_list.rowCount() <= 0:
            return

        best_item = self.live_matches_list.item(0, 0)
        medicine_name = best_item.text().strip() if best_item else ""
        barcode = self._clean_barcode_value(
            best_item.data(Qt.UserRole) if best_item else ""
        )

        if barcode:
            self.process_barcode_routing(
                explicit_barcode=barcode,
                explicit_name=medicine_name
            )
        elif medicine_name:
            self.process_medicine_name_routing(medicine_name)

    def handle_table_row_selection(self, item):
        row = item.row()
        name_item = self.live_matches_list.item(row, 0)
        barcode_item = self.live_matches_list.item(row, 2)

        medicine_name = name_item.text().strip() if name_item else ""
        barcode = self._clean_barcode_value(
            name_item.data(Qt.UserRole) if name_item else ""
        )

        if not barcode and barcode_item:
            barcode = self._clean_barcode_value(barcode_item.text())

        if barcode:
            self.process_barcode_routing(
                explicit_barcode=barcode,
                explicit_name=medicine_name
            )
        elif medicine_name:
            # No barcode is required here. We can still dispense by loading
            # the selected medicine batches from the already cached inventory.
            self.process_medicine_name_routing(medicine_name)
        else:
            show_safe_message(
                self,
                QMessageBox.Warning,
                "Selection Error",
                "The selected medicine could not be identified."
            )

    def process_barcode_routing(self, explicit_barcode=None, explicit_name=None):
        """Load medicine batches using a valid barcode."""
        barcode = self._clean_barcode_value(
            explicit_barcode or self.search_input.text()
        )
        if not barcode:
            show_safe_message(self, QMessageBox.Warning, "Missing Barcode", "Please scan or select a medicine with a valid barcode.")
            return

        self.scanned_barcode = barcode
        self.selected_medicine_name = (explicit_name or "").strip()
        self.batch_table.setRowCount(0)

        try:
            self.loaded_batches = airtable_api.find_all_batches_by_barcode(barcode)

            if not self.loaded_batches and self.all_cached_inventory:
                for item in self.all_cached_inventory:
                    if self._clean_barcode_value(item.get("barcode")) == barcode:
                        self.loaded_batches.append({
                            "id": item["id"],
                            "medicine_name": item["name"],
                            "expiry_date": item["expiry"],
                            "current_quantity": item["qty"],
                            "batch_number": item["batch"]
                        })

            if not self.loaded_batches:
                show_safe_message(
                    self,
                    QMessageBox.Warning,
                    "No Stock",
                    f"No medication records found matching code: {barcode}"
                )
                return

            # A barcode identifies the medicine, not only the specific rows
            # that already contain that barcode. After finding the medicine
            # name, include every available batch with the same medicine name,
            # including older batches saved as NO_BARCODE.
            matched_medicine_name = str(
                self.loaded_batches[0].get("medicine_name", "")
            ).strip()

            existing_ids = {
                str(batch.get("id"))
                for batch in self.loaded_batches
                if batch.get("id") is not None
            }

            if matched_medicine_name:
                for item in self.all_cached_inventory:
                    item_name = str(item.get("name", "")).strip()

                    if item_name.lower() != matched_medicine_name.lower():
                        continue

                    item_id = str(item.get("id"))
                    if item_id in existing_ids:
                        continue

                    current_qty = int(item.get("qty", 0) or 0)
                    if current_qty <= 0:
                        continue

                    self.loaded_batches.append({
                        "id": item.get("id"),
                        "medicine_name": item.get("name", matched_medicine_name),
                        "expiry_date": item.get("expiry") or "9999-12-31",
                        "current_quantity": current_qty,
                        "batch_number": item.get("batch") or "N/A"
                    })
                    existing_ids.add(item_id)

            self.loaded_batches.sort(
                key=lambda batch: str(batch.get("expiry_date", "9999-12-31"))
            )

            self.med_name_title.setText(f"Medicine: {self.loaded_batches[0]['medicine_name']}")
            total_pills = sum(int(b['current_quantity']) for b in self.loaded_batches)
            self.total_stock_lbl.setText(f"Available: {total_pills} pills")

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
                status_item = QTableWidgetItem("First" if idx == 0 else "")

                batch_item.setData(Qt.UserRole, b)

                self.batch_table.setItem(idx, 1, batch_item)
                self.batch_table.setItem(idx, 2, expiry_item)
                self.batch_table.setItem(idx, 3, qty_item)
                self.batch_table.setItem(idx, 4, status_item)

            self.internal_stack.setCurrentIndex(1)
            self.quantity_input.setFocus()

        except Exception as e:
            print(f"Error packing selection grid tables: {e}")

    def process_medicine_name_routing(self, medicine_name):
        """
        Load all available batches for a medicine even when it has no barcode.
        Quantity updates are performed by Airtable/local record ID, so a
        barcode is not required for the actual stock deduction.
        """
        clean_name = str(medicine_name or "").strip()
        if not clean_name:
            show_safe_message(
                self,
                QMessageBox.Warning,
                "Missing Medicine",
                "Please select a valid medicine."
            )
            return

        self.scanned_barcode = "NO_BARCODE"
        self.selected_medicine_name = clean_name
        self.loaded_batches = []
        self.batch_table.setRowCount(0)

        for item in self.all_cached_inventory:
            if str(item.get("name", "")).strip().lower() != clean_name.lower():
                continue

            current_qty = int(item.get("qty", 0) or 0)
            if current_qty <= 0:
                continue

            self.loaded_batches.append({
                "id": item.get("id"),
                "medicine_name": item.get("name", clean_name),
                "expiry_date": item.get("expiry") or "9999-12-31",
                "current_quantity": current_qty,
                "batch_number": item.get("batch") or "N/A"
            })

        if not self.loaded_batches:
            show_safe_message(
                self,
                QMessageBox.Warning,
                "No Stock",
                f"No available stock was found for: {clean_name}"
            )
            return

        self.loaded_batches.sort(key=lambda batch: batch["expiry_date"])

        self.med_name_title.setText(
            f"Medicine: {self.loaded_batches[0]['medicine_name']}"
        )
        total_pills = sum(
            int(batch["current_quantity"])
            for batch in self.loaded_batches
        )
        self.total_stock_lbl.setText(f"Available: {total_pills} pills")

        for idx, batch in enumerate(self.loaded_batches):
            self.batch_table.insertRow(idx)

            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)

            checkbox = QCheckBox()
            checkbox_layout.addWidget(checkbox)
            self.batch_table.setCellWidget(idx, 0, checkbox_widget)

            batch_item = QTableWidgetItem(str(batch["batch_number"]))
            expiry_item = QTableWidgetItem(str(batch["expiry_date"]))
            qty_item = QTableWidgetItem(str(batch["current_quantity"]))
            status_item = QTableWidgetItem("First" if idx == 0 else "")

            batch_item.setData(Qt.UserRole, batch)

            self.batch_table.setItem(idx, 1, batch_item)
            self.batch_table.setItem(idx, 2, expiry_item)
            self.batch_table.setItem(idx, 3, qty_item)
            self.batch_table.setItem(idx, 4, status_item)

        self.internal_stack.setCurrentIndex(1)
        self.quantity_input.setFocus()


    # =====================================================================
    #  HYBRID FIFO ALLOCATION ENGINE
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
                QMessageBox.critical(self, "Insufficient Stock",
                                     f"Requested {requested_qty} pills, but {pool_name} only contains {total_available_in_pool} available!")
                return

            pool_to_calculate.sort(key=lambda x: x["expiry_date"])

            remaining_to_deduct = requested_qty
            allocation_report = []
            allocation_by_expiry = {}
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

                expiry_key = str(batch.get('expiry_date', 'Unknown'))
                allocation_by_expiry[expiry_key] = allocation_by_expiry.get(expiry_key, 0) + pills_to_draw
                execution_plan.append({"id": batch["id"], "old_qty": current_qty, "drawn": pills_to_draw})

            allocation_report = [
                f"Expiry {expiry}: {qty} pills"
                for expiry, qty in allocation_by_expiry.items()
            ]

            # Ask for the doctor first. Pressing Enter inside this dialog confirms the typed name.
            doctor_name = ""
            while True:
                text, ok = QInputDialog.getText(
                    self,
                    "Doctor Name",
                    "Enter doctor name:"
                )

                if not ok:
                    return

                doctor_name = text.strip()
                if doctor_name:
                    break

                QMessageBox.warning(
                    self,
                    "Required Field",
                    "Doctor name is required."
                )

            # Final single confirmation before changing stock.
            medicine_name = self.loaded_batches[0].get("medicine_name", "Unknown") if self.loaded_batches else "Unknown"
            expiry_details = "\n".join(allocation_report) if allocation_report else "No expiry allocation found."
            report_msg = (
                "Please confirm:\n\n"
                f"Medicine: {medicine_name}\n"
                f"Total Quantity: {requested_qty} pills\n\n"
                "Taken from:\n"
                f"{expiry_details}\n\n"
                "Complete this dispense?"
            )

            if not self.ask_upper_confirmation("Confirm Dispense", report_msg):
                return

            # Offline-safe logic.
            for plan in execution_plan:
                new_qty = plan["old_qty"] - plan["drawn"]
                airtable_api.update_medication_quantity(plan["id"], new_qty)

            log_note = "Dispensed to Patient"

            # Offline-safe logic.
            history_barcode = self._clean_barcode_value(self.scanned_barcode)
            if not history_barcode:
                history_barcode = "NO_BARCODE"

            airtable_api.log_transaction(
                "DISPENSE",
                history_barcode,
                self.get_action_by_user_name(),  # Full name of the logged-in staff member
                requested_qty,
                log_note,
                doctor_name=doctor_name
            )

            # No extra success popup: after confirmation the operation is saved and the screen resets.
            self.preload_inventory_cache()
            self.internal_stack.setCurrentIndex(0)
            self.clear_page()

        except ValueError:
            show_safe_message(self, QMessageBox.Warning, "Invalid Quantity", "Please enter a valid quantity.")

    def clear_page(self):
        self.search_input.clear()
        self.quantity_input.clear()
        self.batch_table.setRowCount(0)
        self.live_matches_list.setRowCount(0)
        self.scanned_barcode = ""
        self.selected_medicine_name = ""
        self.loaded_batches = []
        self.internal_stack.setCurrentIndex(0)

        # Refresh default list rendering state automatically on exit contexts
        self.preload_inventory_cache()
        QTimer.singleShot(150, self.focus_barcode_scanner)
