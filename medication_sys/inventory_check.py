import os
import tkinter as tk
from tkinter import ttk
from pyairtable import Api
from dotenv import load_dotenv
import config

# מחפש וטוען את קובץ ה-.env מכל מקום בפרויקט
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, 'tests', '.env')
load_dotenv(env_path)


def fetch_low_stock_medicines():
    """
    מתחבר לאיירטייבל תוך קריאה מותאמת אישית של קובץ ה-.env מתיקיית ה-tests
    """
    try:
        raw_token = os.getenv('AIRTABLE_TOKEN') or config.AIRTABLE_TOKEN
        raw_base_id = os.getenv('BASE_ID') or config.BASE_ID

        if not raw_token or not raw_base_id:
            print(f"❌ Error: Could not find Airtable credentials in: {env_path}")
            return []

        clean_token = str(raw_token).replace('"', '').replace("'", "").strip()
        clean_base_id = str(raw_base_id).replace('"', '').replace("'", "").strip()

        api = Api(clean_token)
        catalog_table = api.table(clean_base_id, 'Medicines Catalog')

        records = catalog_table.all()
        low_stock_list = []

        for record in records:
            fields = record.get('fields', {})

            try:
                min_required = float(fields.get('Minimum Required', 0))
            except (ValueError, TypeError):
                min_required = 0

            try:
                total_valid = float(fields.get('Total Valid Quantity', 0))
            except (ValueError, TypeError):
                total_valid = 0

            if total_valid < min_required:
                low_stock_list.append({
                    'Barcode': fields.get('Barcode', 'Unknown'),
                    'Name': fields.get('Name', 'Unknown'),
                    'Quantity': total_valid
                })

        return low_stock_list

    except Exception as e:
        print(f"\n❌ Airtable Connection Error: {e}\n")
        return []


def show_low_stock_table():
    """
    מייצרת את ממשק הטבלה בעיצוב התואם ל-PyQt5 Dashboard
    """
    data = fetch_low_stock_medicines()

    window = tk.Toplevel()
    window.title("Low Stock Inventory Report")
    window.geometry("600x400")
    window.configure(bg="#F8FAFC")  # צבע רקע תואם למערכת הראשית

    # שימוש בערכת נושא 'clam' כדי לאפשר עיצוב נקי יותר לטבלה ב-Tkinter
    style = ttk.Style()
    style.theme_use('clam')

    # עיצוב כותרות הטבלה
    style.configure("Treeview.Heading", font=('Segoe UI', 12, 'bold'),
                    background="#E2E8F0", foreground="#0F172A")
    # עיצוב שורות הטבלה
    style.configure("Treeview", font=('Segoe UI', 11), rowheight=28,
                    background="#FFFFFF", fieldbackground="#FFFFFF")

    columns = ("Barcode", "Name", "Quantity")
    tree = ttk.Treeview(window, columns=columns, show="headings")

    tree.heading("Barcode", text="Barcode")
    tree.heading("Name", text="Medicine Name")
    tree.heading("Quantity", text="Valid Quantity")

    tree.column("Barcode", width=150, anchor="center")
    tree.column("Name", width=250, anchor="center")
    tree.column("Quantity", width=150, anchor="center")

    for item in data:
        tree.insert("", tk.END, values=(item['Barcode'], item['Name'], item['Quantity']))

    scrollbar = ttk.Scrollbar(window, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    tree.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # כפתור סגירה בעיצוב תואם לקוד הראשי (Red / Cancel Style)
    close_btn = tk.Button(window, text="Close Report", font=('Segoe UI', 13, 'bold'),
                          bg="#EF4444", fg="white", activebackground="#DC2626", activeforeground="white",
                          relief="flat", cursor="hand2", padx=20, pady=5, command=window.destroy)
    close_btn.pack(pady=(0, 15))


# --- בלוק הרצה לבדיקה עצמאית ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Module Test")
    root.geometry("400x250")
    root.configure(bg="#F8FAFC")

    # כפתור בדיקה במסך הראשי בעיצוב תואם לקוד הראשי (Blue / Action Style)
    test_btn = tk.Button(root, text="⚠️ Generate Low Stock Report", font=('Segoe UI', 14, 'bold'),
                         bg="#3B82F6", fg="white", activebackground="#2563EB", activeforeground="white",
                         relief="flat", cursor="hand2", command=show_low_stock_table)
    test_btn.pack(expand=True, fill=tk.BOTH, padx=40, pady=70)

    root.mainloop()