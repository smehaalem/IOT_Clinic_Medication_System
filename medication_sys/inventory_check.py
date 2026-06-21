import requests
import tkinter as tk
from tkinter import ttk

# --- הגדרות ה-API שלך ב-Airtable ---
# יש להחליף את המחרוזות בנתונים האמיתיים של המערכת שלך
AIRTABLE_PAT = 'YOUR_PERSONAL_ACCESS_TOKEN'
BASE_ID = 'YOUR_BASE_ID'
TABLE_NAME = 'Medicines Catalog'


def fetch_low_stock_medicines():
    """
    פונקציה שפונה לאיירטייבל ומושכת רק את התרופות שהכמות התקינה שלהן
    קטנה ממינימום המלאי הנדרש.
    """
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}"
    }

    # אנחנו נותנים לאיירטייבל לעשות את הסינון בשבילנו
    # שימי לב: ודאי ששמות השדות פה זהים בדיוק לשמות באיירטייבל
    params = {
        "filterByFormula": "{Total Valid Quantity} < {Minimum Required}"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Airtable: {e}")
        return []

    low_stock_list = []

    for record in data.get('records', []):
        fields = record.get('fields', {})

        # שולפים את הנתונים הרלוונטיים (עם ערך דיפולטיבי למקרה שחסר)
        name = fields.get('Name', 'Unknown')
        barcode = fields.get('Barcode', 'Unknown')
        valid_qty = fields.get('Total Valid Quantity', 0)

        low_stock_list.append({
            'Barcode': barcode,
            'Name': name,
            'Quantity': valid_qty
        })

    return low_stock_list


def show_low_stock_table():
    """
    פונקציה שמייצרת חלון טבלה וניתנת לחיבור ישירות לכפתור בממשק שלך.
    """
    data = fetch_low_stock_medicines()

    # יצירת חלון קופץ חדש
    window = tk.Toplevel()
    window.title("דו״ח חוסרים במלאי")
    window.geometry("550x350")

    # פונט מותאם למסך מגע
    style = ttk.Style()
    style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))
    style.configure("Treeview", font=('Arial', 11), rowheight=25)

    # הגדרת הטבלה
    columns = ("Barcode", "Name", "Quantity")
    tree = ttk.Treeview(window, columns=columns, show="headings")

    # הגדרת הכותרות
    tree.heading("Barcode", text="ברקוד")
    tree.heading("Name", text="שם התרופה")
    tree.heading("Quantity", text="כמות תקינה (Total Valid)")

    # הגדרת יישור ורוחב עמודות (מותאם למסך של פיי)
    tree.column("Barcode", width=150, anchor="center")
    tree.column("Name", width=200, anchor="center")
    tree.column("Quantity", width=150, anchor="center")

    # הזנת הנתונים לתוך הטבלה
    for item in data:
        tree.insert("", tk.END, values=(item['Barcode'], item['Name'], item['Quantity']))

    # הוספת פס גלילה (Scrollbar) למקרה שיש הרבה חוסרים
    scrollbar = ttk.Scrollbar(window, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # כפתור סגירה נגיש
    close_btn = tk.Button(window, text="סגור חלון", font=('Arial', 12, 'bold'),
                          bg="red", fg="white", command=window.destroy)
    close_btn.pack(pady=10)


# --- בלוק הרצה לבדיקה עצמאית (Test Block) ---
if __name__ == "__main__":
    # יצירת חלון ראשי זמני רק לצורך הבדיקה
    root = tk.Tk()
    root.title("בדיקת ממשק - מסך ראשי זמני")
    root.geometry("300x200")

    # כפתור שמדמה את הכפתור שיהיה לך בממשק האמיתי
    test_btn = tk.Button(root, text="פתח דו״ח חוסרים", font=('Arial', 14, 'bold'),
                         bg="blue", fg="white", command=show_low_stock_table)
    test_btn.pack(expand=True, fill=tk.BOTH, padx=20, pady=50)

    root.mainloop()