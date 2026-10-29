from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
from PIL import Image, ImageTk, ImageOps

# =========================================================
# SMART PARKING DETECTION - FINAL READY PROJECT
# Demo login: admin / admin123
# Modern Tkinter GUI + SQLite + Optional YOLO AI
# =========================================================

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO = None
    YOLO_AVAILABLE = False

AI_AVAILABLE = CV2_AVAILABLE and YOLO_AVAILABLE

DB_NAME = "parking.db"
SLOTS = [f"P{i}" for i in range(1, 21)]

# -------------------- THEME --------------------
BG = "#0f172a"
SIDEBAR = "#111827"
CARD = "#ffffff"
BLUE = "#0284c7"
BLUE_DARK = "#0369a1"
TEXT = "#0f172a"
MUTED = "#64748b"
LIGHT = "#f1f5f9"
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#ea580c"
BORDER = "#cbd5e1"

# =========================================================
# DATABASE
# =========================================================

def db_connect():
    return sqlite3.connect(DB_NAME)

def create_database():
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            vehicle_number TEXT NOT NULL UNIQUE,
            mobile TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            parking_slot TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parking_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parking_slot TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            vehicle_number TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT,
            address TEXT,
            vehicle_number TEXT,
            vehicle_type TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parking_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            owner TEXT NOT NULL,
            parking_slot TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            duration_hours REAL,
            status TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            owner TEXT NOT NULL,
            parking_slot TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            rate_per_hour REAL NOT NULL,
            total_amount REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            payment_time TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating TEXT NOT NULL,
            comments TEXT,
            feedback_time TEXT NOT NULL
        )
    """)

    for slot in SLOTS:
        cur.execute("""
            INSERT OR IGNORE INTO parking_status
            (parking_slot, status, vehicle_number)
            VALUES (?, 'Available', NULL)
        """, (slot,))

    conn.commit()
    conn.close()

def set_slot_status(slot, status, vehicle_number=None):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE parking_status
        SET status=?, vehicle_number=?
        WHERE parking_slot=?
    """, (status, vehicle_number, slot))
    conn.commit()
    conn.close()

def get_slot_data():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT parking_slot, status, vehicle_number
        FROM parking_status ORDER BY id
    """)
    rows = cur.fetchall()
    conn.close()
    return {r[0]: (r[1], r[2]) for r in rows}

# =========================================================
# COMMON UI HELPERS
# =========================================================

def clear_entries(entries):
    for entry in entries:
        entry.delete(0, tk.END)

def valid_mobile(mobile):
    return mobile.isdigit() and len(mobile) == 10

def hover(btn, normal=BLUE, active=BLUE_DARK):
    btn.bind("<Enter>", lambda e: btn.config(bg=active))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal))

def button(parent, text, command, width=18, bg=BLUE, fg="white"):
    b = tk.Button(
        parent, text=text, command=command, width=width,
        font=("Arial", 11, "bold"), bg=bg, fg=fg,
        activebackground=BLUE_DARK, activeforeground="white",
        relief="flat", bd=0, cursor="hand2", pady=8
    )
    hover(b, bg, BLUE_DARK)
    return b

def website_nav(win):
    """Common website-style navigation matching the supplied reference."""
    nav = tk.Frame(win, bg="white", height=72)
    nav.pack(fill="x", side="top")
    nav.pack_propagate(False)

    brand = tk.Frame(nav, bg="white")
    brand.pack(side="left", padx=35)
    tk.Label(brand, text="◉", font=("Arial", 20, "bold"),
             fg="#1677ff", bg="white").pack(side="left", padx=(0, 10))
    bf = tk.Frame(brand, bg="white")
    bf.pack(side="left")
    tk.Label(bf, text="Smart Parking", font=("Arial", 14, "bold"),
             fg=TEXT, bg="white").pack(anchor="w")
    tk.Label(bf, text="Detection System", font=("Arial", 8),
             fg=MUTED, bg="white").pack(anchor="w")

    menu = tk.Frame(nav, bg="white")
    menu.pack(side="right", padx=22)

    items = [
        ("Home", open_dashboard),
        ("Vehicle", vehicle_registration),
        ("Detection", parking_detection),
        ("Billing", payment_billing),
    ]
    for text, cmd in items:
        b = tk.Button(menu, text=text, command=cmd, font=("Arial", 10, "bold"),
                      bg="white", fg=TEXT, activebackground="white",
                      activeforeground="#1677ff", relief="flat", bd=0,
                      cursor="hand2", padx=14)
        b.pack(side="left", padx=2)
    b = tk.Button(menu, text="Logout", command=lambda: logout(win),
                  font=("Arial", 10, "bold"), bg="#111827", fg="white",
                  activebackground="#111827", activeforeground="white",
                  relief="flat", bd=0, cursor="hand2", padx=17, pady=8)
    b.pack(side="left", padx=(10, 0))


def title(parent, text, subtitle=None):
    # Reference-style section banner used by every project form.
    hero = tk.Frame(parent, bg="white", height=145)
    hero.pack(fill="x", padx=15, pady=(10, 0))
    hero.pack_propagate(False)

    left = tk.Frame(hero, bg="white")
    left.pack(side="left", fill="both", expand=True, padx=42, pady=22)
    tk.Label(left, text="SMART PARKING MANAGEMENT", font=("Arial", 9, "bold"),
             fg="#1677ff", bg="white").pack(anchor="w", pady=(0, 8))
    tk.Label(left, text=text.title(), font=("Arial", 27, "bold"),
             fg=TEXT, bg="white").pack(anchor="w")
    if subtitle:
        tk.Label(left, text=subtitle, font=("Arial", 10),
                 fg=MUTED, bg="white").pack(anchor="w", pady=(5, 0))

    badge = tk.Label(hero, text="AI POWERED", font=("Arial", 10, "bold"),
                     fg="#1677ff", bg="#e0f2fe", padx=18, pady=9)
    badge.pack(side="right", padx=42)


def field(parent, label_text, row, width=32):
    tk.Label(parent, text=label_text, font=("Arial", 11, "bold"),
             bg="white", fg=TEXT).grid(row=row, column=0, sticky="w",
                                       padx=18, pady=9)
    e = tk.Entry(parent, font=("Arial", 12), width=width,
                 bd=1, relief="solid", bg="white", fg=TEXT)
    e.grid(row=row, column=1, padx=18, pady=9, ipady=5)
    return e


def open_next(current_window, next_function, delay=150):
    """Switch to the next form without creating another top-level window."""
    global current_page
    try:
        current_window.destroy()
    except tk.TclError:
        pass
    if current_page is current_window:
        current_page = None
    root.after(delay, next_function)


class PageFrame(tk.Frame):
    """A full-window Tkinter Frame that behaves like the old Toplevel forms.
    All project screens stay inside the SAME Tk root, so screen recording
    continues after login and while navigating between forms.
    """
    def __init__(self, parent):
        super().__init__(parent, bg="#0b2024", bd=0, highlightthickness=0)
        self._protocols = {}
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()

    def title(self, *_args):
        pass

    def geometry(self, *_args):
        pass

    def resizable(self, *_args):
        pass

    def state(self, *_args):
        pass

    def protocol(self, name, func):
        self._protocols[name] = func


current_page = None

def new_page():
    """Create the next screen inside the original Tk root."""
    global current_page, dashboard_frame

    if current_page is not None:
        try:
            current_page.destroy()
        except tk.TclError:
            pass
        current_page = None

    try:
        if dashboard_frame is not None:
            dashboard_frame.destroy()
            dashboard_frame = None
    except (NameError, tk.TclError):
        pass

    current_page = PageFrame(root)
    return current_page


def close_page(page):
    """Close a form and return to the dashboard in the same Tk root."""
    global current_page
    try:
        page.destroy()
    except tk.TclError:
        pass
    if current_page is page:
        current_page = None
    root.after(80, open_dashboard)


def setup_window(win, title_text, width, height):
    # Full-screen responsive project forms with the same parking background.
    width = max(width, 980)
    height = max(height + 220, 820)
    win.title(title_text)
    win.geometry(f"{width}x{height}")
    win.resizable(True, True)
    win.state("zoomed")
    win.configure(bg="#0b2024")

    bg_file = Path(__file__).resolve().parent / "parking_background_clean.png"
    try:
        original_bg = Image.open(bg_file).convert("RGB")
        bg_label = tk.Label(win, bd=0, highlightthickness=0)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        bg_label.lower()

        def resize_background(event=None):
            w = max(win.winfo_width(), 1)
            h = max(win.winfo_height(), 1)
            img = ImageOps.fit(original_bg, (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))
            photo = ImageTk.PhotoImage(img)
            bg_label.configure(image=photo)
            bg_label.image = photo

        win.bind("<Configure>", resize_background, add="+")
        win.after(50, resize_background)
    except Exception:
        pass

    website_nav(win)


def table_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Treeview", background="white", foreground=TEXT,
                    rowheight=30, fieldbackground="white", font=("Arial", 10))
    style.configure("Treeview.Heading", background="#e8f4fb", foreground=TEXT,
                    font=("Arial", 10, "bold"))
    style.map("Treeview", background=[("selected", "#dbeafe")],
              foreground=[("selected", TEXT)])

# =========================================================
# 1. ADMIN PROFILE
# =========================================================

def admin_profile():
    win = new_page()
    setup_window(win, "Admin Profile", 620, 560)
    title(win, "ADMIN PROFILE", "Manage administrator information")

    card = tk.Frame(win, bg="white", bd=1, relief="solid")
    card.pack(padx=45, pady=10, fill="x")

    values = [
        ("Admin Name", "Administrator"),
        ("Username", "admin"),
        ("Email", "admin@smartparking.com"),
        ("Mobile Number", "9876543210")
    ]
    entries = {}

    for i, (label, value) in enumerate(values):
        tk.Label(card, text=label, bg="white", fg=TEXT,
                 font=("Arial", 11, "bold")).grid(
                 row=i, column=0, sticky="w", padx=20, pady=12)
        e = tk.Entry(card, font=("Arial", 11), width=32)
        e.insert(0, value)
        if label == "Username":
            e.config(state="readonly")
        e.grid(row=i, column=1, padx=20, pady=12, ipady=5)
        entries[label] = e

    def save():
        mobile = entries["Mobile Number"].get().strip()
        if not all(entries[k].get().strip() for k in
                   ["Admin Name", "Email", "Mobile Number"]):
            messagebox.showwarning("Warning", "Please fill all fields.")
            return
        if not valid_mobile(mobile):
            messagebox.showwarning("Warning", "Enter valid 10 digit mobile number.")
            return
        messagebox.showinfo("Success", "Admin profile updated successfully.")

    button(win, "Save Profile", save, 20).pack(pady=18)
    button(win, "Close", lambda: close_page(win), 20, bg="#64748b").pack()

# =========================================================
# 2. CUSTOMER REGISTRATION
# =========================================================

def customer_registration():
    win = new_page()
    setup_window(win, "Customer Registration", 930, 730)
    title(win, "CUSTOMER REGISTRATION", "Register and manage parking customers")

    card = tk.Frame(win, bg="white", bd=1, relief="solid")
    card.pack(padx=30, pady=5)

    entries = {}
    labels = ["Customer Name", "Mobile Number", "Email", "Address", "Vehicle Number"]

    for i, label_text in enumerate(labels):
        tk.Label(card, text=label_text, font=("Arial", 11, "bold"),
                 bg="white", fg=TEXT).grid(row=i, column=0,
                 padx=15, pady=6, sticky="w")
        e = tk.Entry(card, font=("Arial", 11), width=34)
        e.grid(row=i, column=1, padx=15, pady=6, ipady=4)
        entries[label_text] = e

    tk.Label(card, text="Vehicle Type", font=("Arial", 11, "bold"),
             bg="white", fg=TEXT).grid(row=5, column=0, padx=15, pady=6, sticky="w")
    vtype = ttk.Combobox(card, values=["Car", "Bike", "Bus", "Truck"],
                         state="readonly", width=32)
    vtype.current(0)
    vtype.grid(row=5, column=1, padx=15, pady=6)

    columns = ("ID", "Name", "Mobile", "Email", "Address", "Vehicle", "Type")
    table = ttk.Treeview(win, columns=columns, show="headings", height=7)
    for c in columns:
        table.heading(c, text=c)
        table.column(c, width=125)
    table.pack(padx=15, pady=12)

    def load():
        table.delete(*table.get_children())
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, customer_name, mobile, email, address,
                   vehicle_number, vehicle_type
            FROM customers ORDER BY id DESC
        """)
        for row in cur.fetchall():
            table.insert("", "end", values=row)
        conn.close()

    def clear():
        clear_entries(list(entries.values()))
        vtype.current(0)

    def save():
        vals = {k: e.get().strip() for k, e in entries.items()}
        if any(v == "" for v in vals.values()):
            messagebox.showwarning("Warning", "Please fill all fields.")
            return
        if not valid_mobile(vals["Mobile Number"]):
            messagebox.showwarning("Warning", "Enter valid 10 digit mobile number.")
            return
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO customers
            (customer_name, mobile, email, address, vehicle_number, vehicle_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (vals["Customer Name"], vals["Mobile Number"], vals["Email"],
              vals["Address"], vals["Vehicle Number"].upper(), vtype.get()))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Customer registered successfully. Next form will open automatically.")
        clear()
        load()
        open_next(win, vehicle_registration)

    bf = tk.Frame(win, bg=LIGHT)
    bf.pack(pady=5)
    button(bf, "Save Customer", save, 18).grid(row=0, column=0, padx=5)
    button(bf, "Clear", clear, 18, bg="#64748b").grid(row=0, column=1, padx=5)
    button(bf, "Close", lambda: close_page(win), 18, bg="#475569").grid(row=0, column=2, padx=5)
    load()

# =========================================================
# 3. VEHICLE REGISTRATION
# =========================================================

def vehicle_registration():
    win = new_page()
    setup_window(win, "Vehicle Registration", 820, 700)
    title(win, "VEHICLE REGISTRATION", "Register vehicle and assign a parking slot")

    card = tk.Frame(win, bg="white", bd=1, relief="solid")
    card.pack(padx=50, pady=5)

    owner = field(card, "Owner Name", 0)
    number = field(card, "Vehicle Number", 1)
    mobile = field(card, "Mobile Number", 2)

    tk.Label(card, text="Vehicle Type", font=("Arial", 11, "bold"),
             bg="white", fg=TEXT).grid(row=3, column=0, padx=18, pady=9, sticky="w")
    vtype = ttk.Combobox(card, values=["Car", "Bike", "Bus", "Truck"],
                         state="readonly", width=30)
    vtype.current(0)
    vtype.grid(row=3, column=1, padx=18, pady=9)

    tk.Label(card, text="Parking Slot", font=("Arial", 11, "bold"),
             bg="white", fg=TEXT).grid(row=4, column=0, padx=18, pady=9, sticky="w")
    slot = ttk.Combobox(card, values=SLOTS, state="readonly", width=30)
    slot.grid(row=4, column=1, padx=18, pady=9)

    columns = ("Owner", "Vehicle No", "Mobile", "Type", "Slot")
    table = ttk.Treeview(win, columns=columns, show="headings", height=6)
    for c in columns:
        table.heading(c, text=c)
        table.column(c, width=145)
    table.pack(pady=14)

    def load():
        table.delete(*table.get_children())
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT owner, vehicle_number, mobile, vehicle_type, parking_slot
            FROM vehicles ORDER BY id DESC
        """)
        for row in cur.fetchall():
            table.insert("", "end", values=row)
        conn.close()

    def save():
        o, n, m, t, s = owner.get().strip(), number.get().strip().upper(), mobile.get().strip(), vtype.get(), slot.get()
        if not all([o, n, m, t, s]):
            messagebox.showwarning("Warning", "Please fill all fields.")
            return
        if not valid_mobile(m):
            messagebox.showwarning("Warning", "Enter valid 10 digit mobile number.")
            return
        data = get_slot_data()
        if data.get(s, ("Available", None))[0] == "Occupied":
            messagebox.showerror("Slot Occupied", f"{s} is already occupied.")
            return
        try:
            conn = db_connect()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO vehicles
                (owner, vehicle_number, mobile, vehicle_type, parking_slot)
                VALUES (?, ?, ?, ?, ?)
            """, (o, n, m, t, s))
            cur.execute("""
                UPDATE parking_status
                SET status='Occupied', vehicle_number=?
                WHERE parking_slot=?
            """, (n, s))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Vehicle registered successfully. Parking Slot Management will open automatically.")
            clear_entries([owner, number, mobile])
            vtype.current(0)
            slot.set("")
            load()
            open_next(win, parking_slot_management)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Vehicle number or parking slot already registered.")

    bf = tk.Frame(win, bg=LIGHT)
    bf.pack()
    button(bf, "Save Vehicle", save, 20).grid(row=0, column=0, padx=8)
    button(bf, "Close", lambda: close_page(win), 20, bg="#64748b").grid(row=0, column=1, padx=8)
    load()

# =========================================================
# 4. PARKING SLOT MANAGEMENT
# =========================================================

def parking_slot_management():
    win = new_page()
    setup_window(win, "Parking Slot Management", 850, 680)
    title(win, "PARKING SLOT MANAGEMENT", "Monitor all 20 parking spaces")

    info = tk.Label(win, font=("Arial", 14, "bold"), bg=LIGHT, fg=TEXT)
    info.pack(pady=3)

    frame = tk.Frame(win, bg=LIGHT)
    frame.pack(pady=12)
    buttons = {}
    selected = {"slot": None}

    def refresh():
        data = get_slot_data()
        occupied = 0
        for s in SLOTS:
            status, vehicle = data.get(s, ("Available", None))
            if status == "Occupied":
                occupied += 1
                buttons[s].config(text=f"{s}\nOCCUPIED\n{vehicle or ''}",
                                  bg=RED, fg="white")
            else:
                buttons[s].config(text=f"{s}\nAVAILABLE",
                                  bg=GREEN, fg="white")
        info.config(text=f"Available: {20-occupied}     |     Occupied: {occupied}")

    def select(s):
        selected["slot"] = s
        data = get_slot_data()
        status, vehicle = data.get(s, ("Available", None))
        if status == "Occupied":
            messagebox.showinfo("Slot Details",
                                f"Slot: {s}\nStatus: Occupied\nVehicle: {vehicle or 'Unknown'}")
        else:
            messagebox.showinfo("Slot Details", f"Slot: {s}\nStatus: Available")

    for i, s in enumerate(SLOTS):
        b = tk.Button(frame, text=f"{s}\nAVAILABLE", width=14, height=4,
                      font=("Arial", 10, "bold"), bg=GREEN, fg="white",
                      relief="flat", cursor="hand2",
                      command=lambda x=s: select(x))
        b.grid(row=i//5, column=i%5, padx=8, pady=8)
        buttons[s] = b

    def release():
        s = selected["slot"]
        if not s:
            messagebox.showwarning("Warning", "Click a slot first.")
            return
        data = get_slot_data()
        if data.get(s, ("Available", None))[0] != "Occupied":
            messagebox.showinfo("Info", f"{s} is already available.")
            return
        set_slot_status(s, "Available", None)
        messagebox.showinfo("Success", f"{s} released successfully.")
        selected["slot"] = None
        refresh()

    bf = tk.Frame(win, bg=LIGHT)
    bf.pack(pady=12)
    button(bf, "Refresh", refresh, 18).grid(row=0, column=0, padx=7)
    button(bf, "Release Slot", release, 18, bg=ORANGE).grid(row=0, column=1, padx=7)
    button(bf, "Next: Vehicle Search", lambda: open_next(win, vehicle_search), 20, bg="#0f766e").grid(row=0, column=2, padx=7)
    button(bf, "Close", lambda: close_page(win), 18, bg="#64748b").grid(row=0, column=3, padx=7)
    refresh()

# =========================================================
# 5. VEHICLE SEARCH
# =========================================================

def vehicle_search():
    win = new_page()
    setup_window(win, "Vehicle Search", 720, 620)
    title(win, "VEHICLE SEARCH", "Find registered vehicle details")

    tk.Label(win, text="Vehicle Number", bg=LIGHT, fg=TEXT,
             font=("Arial", 11, "bold")).pack()
    search = tk.Entry(win, font=("Arial", 13), width=32, bd=1, relief="solid")
    search.pack(pady=8, ipady=5)

    box = tk.LabelFrame(win, text=" Vehicle Details ",
                        font=("Arial", 11, "bold"), bg="white",
                        fg=TEXT, padx=20, pady=15)
    box.pack(padx=40, pady=15)

    details = {}
    for i, label_text in enumerate(["Owner Name", "Mobile Number", "Vehicle Type", "Parking Slot"]):
        tk.Label(box, text=label_text, font=("Arial", 11, "bold"),
                 bg="white", fg=TEXT).grid(row=i, column=0,
                 padx=12, pady=9, sticky="w")
        e = tk.Entry(box, font=("Arial", 11), width=30)
        e.config(state="readonly")
        e.grid(row=i, column=1, padx=12, pady=9, ipady=4)
        details[label_text] = e

    result = tk.Label(win, text="Enter vehicle number and search.",
                      font=("Arial", 10), bg=LIGHT, fg=MUTED)
    result.pack()

    def set_value(e, value):
        e.config(state="normal")
        e.delete(0, tk.END)
        e.insert(0, value or "")
        e.config(state="readonly")

    def search_vehicle():
        n = search.get().strip().upper()
        if not n:
            messagebox.showwarning("Warning", "Please enter vehicle number.")
            return
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT owner, mobile, vehicle_type, parking_slot
            FROM vehicles WHERE UPPER(vehicle_number)=?
        """, (n,))
        row = cur.fetchone()
        conn.close()
        if row:
            for e, value in zip(details.values(), row):
                set_value(e, value)
            result.config(text="Vehicle found successfully.", fg=GREEN)
        else:
            for e in details.values():
                set_value(e, "")
            result.config(text="Vehicle not found.", fg=RED)
            messagebox.showerror("Not Found", "This vehicle is not registered.")

    def clear():
        search.delete(0, tk.END)
        for e in details.values():
            set_value(e, "")
        result.config(text="Enter vehicle number and search.", fg=MUTED)

    bf = tk.Frame(win, bg=LIGHT)
    bf.pack(pady=15)
    button(bf, "Search Vehicle", search_vehicle, 18).grid(row=0, column=0, padx=7)
    button(bf, "Clear", clear, 18, bg="#64748b").grid(row=0, column=1, padx=7)
    button(win, "Close", lambda: close_page(win), 20, bg="#475569").pack(pady=5)

# =========================================================
# 6. PARKING ENTRY / EXIT
# =========================================================

def parking_entry_exit():
    win = new_page()
    setup_window(win, "Parking Entry / Exit", 780, 650)
    title(win, "PARKING ENTRY / EXIT", "Record vehicle entry and exit")

    card = tk.Frame(win, bg="white", bd=1, relief="solid")
    card.pack(padx=60, pady=5)

    vehicle = field(card, "Vehicle Number", 0)
    owner = field(card, "Owner Name", 1)

    tk.Label(card, text="Parking Slot", font=("Arial", 11, "bold"),
             bg="white", fg=TEXT).grid(row=2, column=0, padx=18, pady=9, sticky="w")
    slot = ttk.Combobox(card, values=SLOTS, state="readonly", width=30)
    slot.grid(row=2, column=1, padx=18, pady=9)

    status = tk.Label(win, text="Status: Ready", font=("Arial", 12, "bold"),
                      bg=LIGHT, fg=TEXT)
    status.pack(pady=14)

    def find():
        n = vehicle.get().strip().upper()
        if not n:
            messagebox.showwarning("Warning", "Enter vehicle number.")
            return
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT owner, parking_slot FROM vehicles
            WHERE UPPER(vehicle_number)=?
        """, (n,))
        row = cur.fetchone()
        conn.close()
        if not row:
            messagebox.showerror("Not Found", "Vehicle is not registered.")
            return
        vehicle.delete(0, tk.END)
        vehicle.insert(0, n)
        owner.delete(0, tk.END)
        owner.insert(0, row[0])
        slot.set(row[1])
        status.config(text=f"Registered: {n} | Slot: {row[1]}", fg=GREEN)

    def entry():
        n, o, s = vehicle.get().strip().upper(), owner.get().strip(), slot.get()
        if not all([n, o, s]):
            messagebox.showwarning("Warning", "Fill vehicle, owner and slot.")
            return
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM parking_transactions
            WHERE UPPER(vehicle_number)=? AND status='IN'
        """, (n,))
        if cur.fetchone():
            conn.close()
            messagebox.showwarning("Already Inside", "Vehicle already has active entry.")
            return
        cur.execute("SELECT status, vehicle_number FROM parking_status WHERE parking_slot=?", (s,))
        sd = cur.fetchone()
        if sd and sd[0] == "Occupied" and (sd[1] or "").upper() != n:
            conn.close()
            messagebox.showerror("Slot Occupied",
                                 f"{s} is occupied by {sd[1] or 'another vehicle'}.")
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO parking_transactions
            (vehicle_number, owner, parking_slot, entry_time, status)
            VALUES (?, ?, ?, ?, 'IN')
        """, (n, o, s, now))
        cur.execute("""
            UPDATE parking_status SET status='Occupied', vehicle_number=?
            WHERE parking_slot=?
        """, (n, s))
        conn.commit()
        conn.close()
        status.config(text=f"Status: IN | {now}", fg=GREEN)
        messagebox.showinfo("Success",
                            f"Parking entry recorded.\nSlot: {s}\nEntry: {now}")

    def exit_vehicle():
        n = vehicle.get().strip().upper()
        if not n:
            messagebox.showwarning("Warning", "Enter vehicle number.")
            return
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, owner, parking_slot, entry_time
            FROM parking_transactions
            WHERE UPPER(vehicle_number)=? AND status='IN'
            ORDER BY id DESC LIMIT 1
        """, (n,))
        row = cur.fetchone()
        if not row:
            conn.close()
            messagebox.showerror("Not Found", "No active parking entry found.")
            return
        tid, o, s, entry_time = row
        exit_dt = datetime.now()
        entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
        duration = max(0, (exit_dt-entry_dt).total_seconds()/3600)
        exit_time = exit_dt.strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            UPDATE parking_transactions
            SET exit_time=?, duration_hours=?, status='OUT'
            WHERE id=?
        """, (exit_time, duration, tid))
        cur.execute("""
            UPDATE parking_status SET status='Available', vehicle_number=NULL
            WHERE parking_slot=?
        """, (s,))
        conn.commit()
        conn.close()
        owner.delete(0, tk.END)
        owner.insert(0, o)
        slot.set(s)
        status.config(text=f"Status: OUT | {exit_time}", fg=ORANGE)
        messagebox.showinfo(
            "Success",
            f"Vehicle: {n}\nSlot: {s}\nDuration: {duration:.2f} hours\n\nPayment / Billing will open automatically."
        )
        open_next(win, lambda: payment_billing(duration))

    def clear():
        vehicle.delete(0, tk.END)
        owner.delete(0, tk.END)
        slot.set("")
        status.config(text="Status: Ready", fg=TEXT)

    bf = tk.Frame(win, bg=LIGHT)
    bf.pack(pady=15)
    button(bf, "Find Vehicle", find, 16).grid(row=0, column=0, padx=4)
    button(bf, "Process Entry", entry, 16, bg=GREEN).grid(row=0, column=1, padx=4)
    button(bf, "Process Exit", exit_vehicle, 16, bg=ORANGE).grid(row=0, column=2, padx=4)
    button(bf, "Clear", clear, 16, bg="#64748b").grid(row=0, column=3, padx=4)
    button(win, "Close", lambda: close_page(win), 20, bg="#475569").pack()

# =========================================================
# 7. AI PARKING DETECTION
# =========================================================

def parking_detection():
    if not AI_AVAILABLE:
        messagebox.showerror(
            "AI Error",
            "OpenCV/Ultralytics is not installed.\n\n"
            "Run:\npip install opencv-python ultralytics"
        )
        return

    win = new_page()
    setup_window(win, "AI Smart Parking Detection", 920, 700)
    title(win, "AI SMART PARKING DETECTION", "YOLO based vehicle and slot detection")

    info = tk.Label(win, text="Available: 20    Occupied: 0",
                    font=("Arial", 13, "bold"), bg=LIGHT, fg=TEXT)
    info.pack()

    video = tk.Label(win, bg="black")
    video.pack(pady=8)

    try:
        model = YOLO("yolo11n.pt")
    except Exception as e:
        win.destroy()
        messagebox.showerror("AI Model Error",
                             f"Could not load yolo11n.pt.\n\n{e}")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        win.destroy()
        messagebox.showerror("Camera Error", "Camera could not be opened.")
        return

    slots = []
    start_x, start_y = 50, 30
    w, h, gx, gy = 120, 80, 15, 15
    for r in range(4):
        for c in range(5):
            x1 = start_x + c*(w+gx)
            y1 = start_y + r*(h+gy)
            slots.append((x1, y1, x1+w, y1+h))

    running = {"value": True}

    def close():
        running["value"] = False
        if cap.isOpened():
            cap.release()
        close_page(win)

    def update():
        if not running["value"]:
            return
        ret, frame = cap.read()
        if not ret:
            close()
            return

        frame = cv2.resize(frame, (700, 500))
        results = model(frame, verbose=False)
        boxes = []

        for box in results[0].boxes:
            cid = int(box.cls[0])
            name = model.names[cid]
            if name in ["car", "motorcycle", "bus", "truck"]:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((x1, y1, x2, y2))
                cv2.rectangle(frame, (x1,y1), (x2,y2), (255,0,0), 2)
                cv2.putText(frame, name, (x1,y1-7),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (255,0,0), 2)

        occupied = 0
        conn = db_connect()
        cur = conn.cursor()

        for i, (x1,y1,x2,y2) in enumerate(slots):
            occ = False
            for vx1,vy1,vx2,vy2 in boxes:
                cx, cy = (vx1+vx2)//2, (vy1+vy2)//2
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    occ = True
                    break

            s = SLOTS[i]
            if occ:
                occupied += 1
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,0,255), 3)
                cv2.putText(frame, f"{s} OCCUPIED", (x1,y1+23),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,255), 2)
                cur.execute("""
                    UPDATE parking_status
                    SET status='Occupied', vehicle_number=NULL
                    WHERE parking_slot=?
                """, (s,))
            else:
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                cv2.putText(frame, f"{s} AVAILABLE", (x1,y1+23),
                            cv2.FONT_HERSHEY_SIMPLEX, .5, (0,255,0), 2)
                cur.execute("""
                    UPDATE parking_status
                    SET status='Available', vehicle_number=NULL
                    WHERE parking_slot=?
                """, (s,))

        conn.commit()
        conn.close()

        info.config(text=f"Available: {20-occupied}    Occupied: {occupied}")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ok, encoded = cv2.imencode(".png", rgb)
        if ok:
            image = tk.PhotoImage(data=encoded.tobytes())
            video.config(image=image)
            video.image = image

        win.after(40, update)

    button(win, "Close", close, 20, bg="#475569").pack(pady=8)
    win.protocol("WM_DELETE_WINDOW", close)
    update()

# =========================================================
# 8. PARKING HISTORY
# =========================================================

def parking_history():
    win = new_page()
    setup_window(win, "Parking History", 1100, 600)
    title(win, "PARKING HISTORY", "All vehicle entry and exit records")

    columns = ("ID","Vehicle","Owner","Slot","Entry","Exit","Duration","Status")
    table = ttk.Treeview(win, columns=columns, show="headings", height=17)
    widths = [50,120,130,70,150,150,90,80]
    for c,w in zip(columns,widths):
        table.heading(c,text=c)
        table.column(c,width=w)
    table.pack(padx=10,pady=10)

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, vehicle_number, owner, parking_slot,
               entry_time, COALESCE(exit_time,''),
               COALESCE(ROUND(duration_hours,2),0), status
        FROM parking_transactions ORDER BY id DESC
    """)
    for row in cur.fetchall():
        table.insert("", "end", values=row)
    conn.close()

    button(win, "Close", lambda: close_page(win), 20, bg="#475569").pack(pady=8)

# =========================================================
# 9. PAYMENT / BILLING
# =========================================================

def payment_billing(prefill_duration=None):
    win = new_page()
    setup_window(win, "Payment / Billing", 720, 650)
    title(win, "PARKING PAYMENT / BILLING", "Generate and record parking payment")

    card = tk.Frame(win, bg="white", bd=1, relief="solid")
    card.pack(padx=50, pady=5)

    vehicle = field(card, "Vehicle Number", 0)
    owner = field(card, "Owner Name", 1)
    slot = field(card, "Parking Slot", 2)
    duration = field(card, "Duration (Hours)", 3)
    rate = field(card, "Rate Per Hour (₹)", 4)
    rate.insert(0, "20")

    tk.Label(card, text="Payment Mode", font=("Arial", 11, "bold"),
             bg="white", fg=TEXT).grid(row=5,column=0,padx=18,pady=9,sticky="w")
    mode = ttk.Combobox(card, values=["Cash","UPI","Card"],
                        state="readonly", width=30)
    mode.current(0)
    mode.grid(row=5,column=1,padx=18,pady=9)

    total = tk.Label(win, text="Total Amount: ₹0.00",
                     font=("Arial", 18, "bold"), bg=LIGHT, fg=BLUE_DARK)
    total.pack(pady=18)

    def find():
        n = vehicle.get().strip().upper()
        if not n:
            messagebox.showwarning("Warning","Enter vehicle number.")
            return
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT owner,parking_slot FROM vehicles
            WHERE UPPER(vehicle_number)=?
        """,(n,))
        row = cur.fetchone()
        conn.close()
        if row:
            owner.delete(0,tk.END)
            owner.insert(0,row[0])
            slot.delete(0,tk.END)
            slot.insert(0,row[1])
        else:
            messagebox.showerror("Not Found","Vehicle is not registered.")

    def bill():
        try:
            d=float(duration.get())
            r=float(rate.get())
            if d<=0 or r<=0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Duration and rate must be positive numbers.")
            return

        n,o,s=vehicle.get().strip().upper(),owner.get().strip(),slot.get().strip()
        if not all([n,o,s]):
            messagebox.showwarning("Warning","Please fill vehicle details.")
            return

        amount=d*r
        total.config(text=f"Total Amount: ₹{amount:.2f}")

        conn=db_connect()
        cur=conn.cursor()
        cur.execute("""
            INSERT INTO payments
            (vehicle_number,owner,parking_slot,duration_hours,
             rate_per_hour,total_amount,payment_mode,payment_time)
            VALUES (?,?,?,?,?,?,?,?)
        """,(n,o,s,d,r,amount,mode.get(),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        messagebox.showinfo(
            "Payment Successful",
            f"Vehicle: {n}\nAmount: ₹{amount:.2f}\nMode: {mode.get()}\n\nParking History will open automatically."
        )
        open_next(win, parking_history)

    bf=tk.Frame(win,bg=LIGHT)
    bf.pack(pady=8)
    button(bf,"Find Vehicle",find,18).grid(row=0,column=0,padx=8)
    button(bf,"Generate Bill",bill,18,bg=GREEN).grid(row=0,column=1,padx=8)
    button(win,"Close",lambda: close_page(win),20,bg="#475569").pack(pady=10)

# =========================================================
# 10. PAYMENT HISTORY
# =========================================================

def payment_history():
    win=new_page()
    setup_window(win,"Payment History",1000,560)
    title(win,"PAYMENT HISTORY / REPORT","All parking payment records")

    columns=("ID","Vehicle","Owner","Slot","Hours","Rate","Amount","Mode","Date")
    table=ttk.Treeview(win,columns=columns,show="headings",height=17)
    for c in columns:
        table.heading(c,text=c)
        table.column(c,width=105)
    table.pack(padx=10,pady=10)

    conn=db_connect()
    cur=conn.cursor()
    cur.execute("""
        SELECT id,vehicle_number,owner,parking_slot,
               duration_hours,rate_per_hour,total_amount,
               payment_mode,payment_time
        FROM payments ORDER BY id DESC
    """)
    for row in cur.fetchall():
        table.insert("", "end", values=row)
    conn.close()

    button(win,"Close",lambda: close_page(win),20,bg="#475569").pack(pady=8)

# =========================================================
# 11. FEEDBACK
# =========================================================

def feedback_form():
    win=new_page()
    setup_window(win,"Customer Feedback",650,560)
    title(win,"CUSTOMER FEEDBACK","Share your experience with the parking system")

    card=tk.Frame(win,bg="white",bd=1,relief="solid")
    card.pack(padx=40,pady=5)

    tk.Label(card,text="Name",font=("Arial",11,"bold"),
             bg="white",fg=TEXT).grid(row=0,column=0,padx=15,pady=10)
    name=tk.Entry(card,font=("Arial",11),width=32)
    name.grid(row=0,column=1,padx=15,pady=10,ipady=4)

    tk.Label(card,text="Rating",font=("Arial",11,"bold"),
             bg="white",fg=TEXT).grid(row=1,column=0,padx=15,pady=10)
    rating=ttk.Combobox(card,
        values=["Excellent","Very Good","Good","Average","Poor"],
        state="readonly",width=30)
    rating.current(0)
    rating.grid(row=1,column=1,padx=15,pady=10)

    tk.Label(card,text="Comments",font=("Arial",11,"bold"),
             bg="white",fg=TEXT).grid(row=2,column=0,padx=15,pady=10,sticky="n")
    comments=tk.Text(card,width=32,height=7,font=("Arial",11))
    comments.grid(row=2,column=1,padx=15,pady=10)

    def save():
        n=name.get().strip()
        c=comments.get("1.0",tk.END).strip()
        if not n:
            messagebox.showwarning("Warning","Enter your name.")
            return
        conn=db_connect()
        cur=conn.cursor()
        cur.execute("""
            INSERT INTO feedback(name,rating,comments,feedback_time)
            VALUES(?,?,?,?)
        """,(n,rating.get(),c,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        messagebox.showinfo("Thank You","Feedback submitted successfully.")
        name.delete(0,tk.END)
        comments.delete("1.0",tk.END)

    button(win,"Submit Feedback",save,22).pack(pady=15)
    button(win,"Close",lambda: close_page(win),22,bg="#475569").pack()

# =========================================================
# 12. PARKING REPORT
# =========================================================

def parking_report():
    win=new_page()
    setup_window(win,"Parking Report",700,520)
    title(win,"PARKING REPORT","Current parking statistics")

    data=get_slot_data()
    occupied=sum(
        1 for s in SLOTS
        if data.get(s,("Available",None))[0]=="Occupied"
    )

    conn=db_connect()
    cur=conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vehicles")
    vehicles=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM parking_transactions WHERE status='IN'")
    active=cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(total_amount),0) FROM payments")
    revenue=cur.fetchone()[0]
    conn.close()

    card=tk.Frame(win,bg="white",bd=1,relief="solid")
    card.pack(padx=80,pady=10)

    stats=[
        ("Total Parking Slots","20"),
        ("Available Slots",str(20-occupied)),
        ("Occupied Slots",str(occupied)),
        ("Registered Vehicles",str(vehicles)),
        ("Active Entries",str(active)),
        ("Total Revenue",f"₹{revenue:.2f}")
    ]

    for i,(a,b) in enumerate(stats):
        tk.Label(card,text=a,font=("Arial",12,"bold"),
                 bg="white",fg=TEXT).grid(
                 row=i,column=0,padx=35,pady=10,sticky="w")
        tk.Label(card,text=b,font=("Arial",12),
                 bg="white",fg=BLUE_DARK).grid(
                 row=i,column=1,padx=35,pady=10)

    button(win,"Close",lambda: close_page(win),20,bg="#475569").pack(pady=20)

# =========================================================
# 13. NOTIFICATIONS
# =========================================================

def notifications():
    win=new_page()
    setup_window(win,"Notifications",650,500)
    title(win,"SYSTEM NOTIFICATIONS","Current system and parking status")

    data=get_slot_data()
    occupied=[
        s for s in SLOTS
        if data.get(s,("Available",None))[0]=="Occupied"
    ]

    messages=[
        "System is running normally.",
        "Total parking slots: 20",
        f"Occupied slots: {len(occupied)}",
        f"Available slots: {20-len(occupied)}",
        f"Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]

    card=tk.Frame(win,bg="white",bd=1,relief="solid")
    card.pack(padx=50,pady=10,fill="x")

    for m in messages:
        tk.Label(card,text="●  "+m,font=("Arial",11),
                 anchor="w",bg="white",fg=TEXT).pack(
                 padx=25,pady=10,fill="x")

    button(win,"Close",lambda: close_page(win),20,bg="#475569").pack(pady=20)

# =========================================================
# 14. SETTINGS
# =========================================================

def settings():
    win=new_page()
    setup_window(win,"System Settings",650,520)
    title(win,"SYSTEM SETTINGS","Configure basic parking system settings")

    card=tk.Frame(win,bg="white",bd=1,relief="solid")
    card.pack(padx=60,pady=10)

    tk.Label(card,text="Parking Rate Per Hour (₹)",
             font=("Arial",11,"bold"),bg="white",fg=TEXT).grid(
             row=0,column=0,padx=18,pady=12)
    rate=tk.Entry(card,font=("Arial",11),width=25)
    rate.insert(0,"20")
    rate.grid(row=0,column=1,padx=18,pady=12,ipady=4)

    tk.Label(card,text="Total Parking Slots",
             font=("Arial",11,"bold"),bg="white",fg=TEXT).grid(
             row=1,column=0,padx=18,pady=12)
    total=tk.Entry(card,font=("Arial",11),width=25)
    total.insert(0,"20")
    total.config(state="readonly")
    total.grid(row=1,column=1,padx=18,pady=12,ipady=4)

    tk.Label(card,text="Vehicle Types",
             font=("Arial",11,"bold"),bg="white",fg=TEXT).grid(
             row=2,column=0,padx=18,pady=12)
    types=tk.Entry(card,font=("Arial",11),width=25)
    types.insert(0,"Car, Bike, Bus, Truck")
    types.config(state="readonly")
    types.grid(row=2,column=1,padx=18,pady=12,ipady=4)

    def save():
        try:
            if float(rate.get())<=0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Enter a valid positive rate.")
            return
        messagebox.showinfo("Saved","Settings saved successfully.")

    button(win,"Save Settings",save,20).pack(pady=25)
    button(win,"Close",lambda: close_page(win),20,bg="#475569").pack()

# =========================================================
# 15. HELP / ABOUT
# =========================================================

def help_about():
    win=new_page()
    setup_window(win,"Help / About Project",700,600)
    title(win,"SMART PARKING DETECTION","Project information and login details")

    card=tk.Frame(win,bg="white",bd=1,relief="solid")
    card.pack(padx=45,pady=10,fill="both",expand=False)

    text=(
        "PROJECT: SMART PARKING DETECTION\n\n"
        "This system provides:\n\n"
        "• Customer and vehicle registration\n"
        "• Parking slot management\n"
        "• Vehicle search / find vehicle\n"
        "• Parking entry and exit\n"
        "• AI vehicle detection using YOLO\n"
        "• Parking history\n"
        "• Payment and billing\n"
        "• Payment history and reports\n"
        "• Customer feedback\n"
        "• System notifications\n"
        "• System settings\n\n"
        "Technology: Python + Tkinter + SQLite + OpenCV + YOLO\n\n"
        "Demo Login\n"
        "Username: admin\n"
        "Password: admin123"
    )

    tk.Label(card,text=text,font=("Arial",11),justify="left",
             bg="white",fg=TEXT).pack(
             padx=30,pady=25,anchor="w")

    button(win,"Close",lambda: close_page(win),20,bg="#475569").pack(pady=15)

# =========================================================
# LOGOUT
# =========================================================

def logout(dashboard):
    """Return to login while keeping the original Tk root window."""
    global current_page, dashboard_frame
    try:
        dashboard.destroy()
    except tk.TclError:
        pass
    current_page = None
    dashboard_frame = None
    try:
        left_frame.place(relx=0.5, rely=0.5, x=-455, y=-280)
        right_frame.place(relx=0.5, rely=0.5, x=10, y=-280)
        username_entry.delete(0,tk.END)
        password_entry.delete(0,tk.END)
        username_entry.focus()
    except (NameError, tk.TclError):
        pass


# Main dashboard container. It is a Frame inside the original Tk root.
dashboard_frame = None

# =========================================================
# DASHBOARD
# =========================================================

def open_dashboard():
    global dashboard_frame, current_page

    if current_page is not None:
        try:
            current_page.destroy()
        except tk.TclError:
            pass
        current_page = None

    # Reuse the SAME Tk root. Do not create a Toplevel here.
    # Xbox Game Bar can otherwise go black when the login window is replaced
    # by a separate Tkinter window.
    if dashboard_frame is not None:
        try:
            dashboard_frame.destroy()
        except tk.TclError:
            pass

    dashboard_frame = tk.Frame(root, bg="#0b2024")
    dashboard_frame.place(x=0, y=0, relwidth=1, relheight=1)
    dashboard = dashboard_frame
    website_nav(dashboard)

    # Responsive full-window parking background.
    bg_file = Path(__file__).resolve().parent / "parking_background_clean.png"
    try:
        original_bg = Image.open(bg_file).convert("RGB")
        bg_label = tk.Label(dashboard, bd=0, highlightthickness=0)
        bg_label.place(x=0, y=72, relwidth=1, relheight=1, anchor="nw")
        bg_label.lower()

        def resize_dashboard_bg(event=None):
            w = max(dashboard.winfo_width(), 1)
            h = max(dashboard.winfo_height() - 72, 1)
            img = ImageOps.fit(original_bg, (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))
            photo = ImageTk.PhotoImage(img)
            bg_label.configure(image=photo)
            bg_label.image = photo

        dashboard.bind("<Configure>", resize_dashboard_bg, add="+")
        dashboard.after(50, resize_dashboard_bg)
    except Exception:
        pass

    # Dark transparent-like hero panel on the left
    hero = tk.Frame(dashboard, bg="#07191c", width=650, height=500)
    hero.place(x=55, y=120)
    hero.pack_propagate(False)

    tk.Label(hero, text="SMART SOLUTION FOR SMART CITIES",
             font=("Arial", 11, "bold"), fg="#12c7b4", bg="#07191c").pack(
             anchor="w", padx=28, pady=(28, 0))
    tk.Label(hero, text="Smart Parking\nDetection System",
             font=("Arial", 34, "bold"), justify="left",
             fg="white", bg="#07191c").pack(anchor="w", padx=28, pady=(28, 5))
    tk.Label(hero, text="AI Based Smart Parking Management",
             font=("Arial", 16, "bold"), fg="white", bg="#07191c").pack(
             anchor="w", padx=28, pady=(5, 15))
    tk.Label(hero, text="Detect, Monitor and Manage Parking Slots with the Power of AI.\nMake Parking Smarter, Safer and More Efficient.",
             font=("Arial", 11), justify="left", fg="#e2e8f0", bg="#07191c").pack(
             anchor="w", padx=28)

    bf = tk.Frame(hero, bg="#07191c")
    bf.pack(anchor="w", padx=28, pady=25)
    button(bf, "GET STARTED", vehicle_registration, 16).pack(side="left", padx=(0, 18))
    tk.Button(bf, text="VIEW PARKING", command=parking_slot_management,
              font=("Arial", 10, "bold"), bg="#07191c", fg="white",
              activebackground="#07191c", activeforeground="#12c7b4",
              relief="solid", bd=1, cursor="hand2", padx=15, pady=9).pack(side="left")

    quick = tk.Frame(hero, bg="#07191c")
    quick.pack(anchor="w", padx=28, pady=(0, 8))
    for txt, cmd in [
        ("CUSTOMER", customer_registration),
        ("ENTRY / EXIT", parking_entry_exit),
        ("HISTORY", parking_history),
        ("REPORT", parking_report),
        ("FEEDBACK", feedback_form),
    ]:
        tk.Button(
            quick, text=txt, command=cmd, font=("Arial", 9, "bold"),
            bg="#0f2a2e", fg="white", activebackground="#12383d",
            activeforeground="#12c7b4", relief="solid", bd=1,
            cursor="hand2", padx=9, pady=6
        ).pack(side="left", padx=(0, 7))

    data = get_slot_data()
    occupied = sum(1 for s in SLOTS if data.get(s, ("Available", None))[0] == "Occupied")
    conn = db_connect(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vehicles")
    registered = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payments")
    payments = cur.fetchone()[0]
    conn.close()

    stats = tk.Frame(dashboard, bg="white", height=85)
    stats.place(x=55, y=635, width=1090)
    stats.pack_propagate(False)
    for i, (label_text, value) in enumerate([
        ("TOTAL SLOTS", len(SLOTS)), ("OCCUPIED", occupied),
        ("AVAILABLE", len(SLOTS)-occupied), ("REGISTERED VEHICLES", registered),
        ("PAYMENTS", payments)]):
        box = tk.Frame(stats, bg="white", width=218, height=85)
        box.grid(row=0, column=i, sticky="nsew")
        stats.grid_columnconfigure(i, weight=1)
        tk.Label(box, text=str(value), font=("Arial", 20, "bold"),
                 fg="#11ad9c", bg="white").pack(pady=(13, 0))
        tk.Label(box, text=label_text, font=("Arial", 8, "bold"),
                 fg="#64748b", bg="white").pack()


# =========================================================
# LOGIN
# =========================================================

def login():
    username=username_entry.get().strip()
    password=password_entry.get().strip()

    if not username or not password:
        messagebox.showwarning(
            "Warning","Please enter username and password.")
        return

    if username=="admin" and password=="admin123":
        # Keep the main Tk root visible; dashboard is now a Frame in the same window.
        try:
            left_frame.place_forget()
            right_frame.place_forget()
        except tk.TclError:
            pass
        open_dashboard()
    else:
        messagebox.showerror(
            "Login Failed",
            "Invalid username or password.")

# =========================================================
# MAIN - MODERN LOGIN PAGE
# =========================================================

# Create the main Tkinter root BEFORE ttk.Style().
# This avoids creating an unwanted default Tk root on some systems.
root=tk.Tk()
root.title("Smart Parking Detection")
root.geometry("1000x650")
root.resizable(True, True)
root.state("zoomed")
root.configure(bg=BG)

# Initialize database and ttk styling after the root exists.
create_database()
table_style()

# =========================================================
# LOGIN PAGE - SAME PARKING BACKGROUND AS ALL FORMS
# =========================================================

bg_file = Path(__file__).resolve().parent / "parking_background_clean.png"
try:
    original_login_bg = Image.open(bg_file).convert("RGB")
    login_bg_label = tk.Label(root, bd=0, highlightthickness=0)
    login_bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    login_bg_label.lower()

    def resize_login_background(event=None):
        w = max(root.winfo_width(), 1)
        h = max(root.winfo_height(), 1)
        img = ImageOps.fit(original_login_bg, (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))
        photo = ImageTk.PhotoImage(img)
        login_bg_label.configure(image=photo)
        login_bg_label.image = photo

    root.bind("<Configure>", resize_login_background, add="+")
    root.after(50, resize_login_background)
except Exception:
    pass

# Dark brand card on the left
left_frame = tk.Frame(root, bg=SIDEBAR, width=455, height=560)
left_frame.place(relx=0.5, rely=0.5, x=-455, y=-280)
left_frame.pack_propagate(False)

tk.Label(left_frame, text="SMART", font=("Arial", 38, "bold"),
         fg="#38bdf8", bg=SIDEBAR).pack(pady=(95, 0))
tk.Label(left_frame, text="PARKING", font=("Arial", 38, "bold"),
         fg="white", bg=SIDEBAR).pack()
tk.Label(left_frame, text="DETECTION", font=("Arial", 38, "bold"),
         fg="#38bdf8", bg=SIDEBAR).pack()
tk.Label(left_frame,
         text="AI Based Smart Parking Management System",
         font=("Arial", 11), fg="#cbd5e1", bg=SIDEBAR).pack(pady=18)
tk.Frame(left_frame, bg="#38bdf8", height=2, width=280).pack(pady=6)
tk.Label(left_frame,
         text="Easy Parking  •  AI Detection  •  Smart Reports",
         font=("Arial", 10), fg="#94a3b8", bg=SIDEBAR).pack(pady=12)
tk.Label(left_frame, text="20 Parking Slots",
         font=("Arial", 11, "bold"),
         fg="#7dd3fc", bg=SIDEBAR).pack(pady=22)

# White login card on the right
right_frame = tk.Frame(root, bg="#f8fafc", width=390, height=560)
right_frame.place(relx=0.5, rely=0.5, x=65, y=-280)
right_frame.pack_propagate(False)

tk.Label(right_frame, text="Welcome Back!",
         font=("Arial", 28, "bold"),
         fg=TEXT, bg="#f8fafc").pack(pady=(72, 5))
tk.Label(right_frame,
         text="Login to your parking management system",
         font=("Arial", 10), fg=MUTED, bg="#f8fafc").pack(pady=(0, 28))

tk.Label(right_frame, text="Username",
         font=("Arial", 11, "bold"), fg=TEXT, bg="#f8fafc").pack(anchor="w", padx=55)
username_entry = tk.Entry(right_frame, font=("Arial", 13), width=28,
                          bd=1, relief="solid", bg="white")
username_entry.pack(pady=(8, 18), ipady=8)

tk.Label(right_frame, text="Password",
         font=("Arial", 11, "bold"), fg=TEXT, bg="#f8fafc").pack(anchor="w", padx=55)
password_entry = tk.Entry(right_frame, font=("Arial", 13), width=28,
                          bd=1, relief="solid", bg="white", show="*")
password_entry.pack(pady=(8, 5), ipady=8)

show_password = tk.BooleanVar(value=False)

def toggle_password():
    password_entry.config(show="" if show_password.get() else "*")

tk.Checkbutton(
    right_frame, text="Show Password", variable=show_password,
    command=toggle_password, font=("Arial", 10),
    bg="#f8fafc", fg=MUTED, activebackground="#f8fafc",
    activeforeground=TEXT
).pack(anchor="w", padx=53, pady=(0, 16))

login_button = button(right_frame, "LOGIN", login, width=24)
login_button.pack(pady=6)

exit_button = button(right_frame, "EXIT", root.destroy,
                     width=24, bg="#cbd5e1", fg=TEXT)
exit_button.pack(pady=9)

tk.Label(right_frame, text="Demo Login",
         font=("Arial", 10, "bold"),
         fg=MUTED, bg="#f8fafc").pack(pady=(17, 3))
tk.Label(right_frame,
         text="Username: admin  |  Password: admin123",
         font=("Arial", 9), fg="#5977a0", bg="#f8fafc").pack()

root.bind("<Return>",lambda event:login())
username_entry.focus()

# Clean application shutdown.
def close_application():
    try:
        root.destroy()
    except tk.TclError:
        pass

root.protocol("WM_DELETE_WINDOW", close_application)
root.mainloop()
