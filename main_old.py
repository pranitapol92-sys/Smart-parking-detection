import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

try:
    import cv2
    from ultralytics import YOLO
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


DB_NAME = "parking.db"
SLOTS = [f"P{i}" for i in range(1, 21)]


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
        SET status = ?, vehicle_number = ?
        WHERE parking_slot = ?
    """, (status, vehicle_number, slot))
    conn.commit()
    conn.close()


def get_slot_data():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT parking_slot, status, vehicle_number
        FROM parking_status
        ORDER BY id
    """)
    rows = cur.fetchall()
    conn.close()
    return {r[0]: (r[1], r[2]) for r in rows}


# =========================================================
# COMMON HELPERS
# =========================================================

def clear_entries(entries):
    for entry in entries:
        entry.delete(0, tk.END)


def valid_mobile(mobile):
    return mobile.isdigit() and len(mobile) == 10


# =========================================================
# 1. ADMIN PROFILE
# =========================================================

def admin_profile():
    win = tk.Toplevel(root)
    win.title("Admin Profile")
    win.geometry("600x560")
    win.resizable(False, False)

    tk.Label(win, text="ADMIN PROFILE",
             font=("Arial", 22, "bold")).pack(pady=25)

    frame = tk.Frame(win)
    frame.pack(pady=10)

    fields = {}
    for i, (label, value) in enumerate([
        ("Admin Name", "Administrator"),
        ("Username", "admin"),
        ("Email", "admin@smartparking.com"),
        ("Mobile Number", "9876543210")
    ]):
        tk.Label(frame, text=label, font=("Arial", 12)).grid(
            row=i, column=0, padx=15, pady=10, sticky="w")
        e = tk.Entry(frame, font=("Arial", 12), width=32)
        e.insert(0, value)
        if label == "Username":
            e.config(state="readonly")
        e.grid(row=i, column=1, padx=15, pady=10)
        fields[label] = e

    def save():
        mobile = fields["Mobile Number"].get().strip()
        if not all(fields[k].get().strip() for k in
                   ["Admin Name", "Email", "Mobile Number"]):
            messagebox.showwarning("Warning", "Please fill all fields.")
            return
        if not valid_mobile(mobile):
            messagebox.showwarning("Warning", "Enter valid 10 digit mobile number.")
            return
        messagebox.showinfo("Success", "Admin profile updated successfully.")

    tk.Button(win, text="Save Profile", width=20,
              font=("Arial", 12, "bold"), command=save).pack(pady=20)
    tk.Button(win, text="Close", width=20,
              command=win.destroy).pack()


# =========================================================
# 2. CUSTOMER REGISTRATION
# =========================================================

def customer_registration():
    win = tk.Toplevel(root)
    win.title("Customer Registration")
    win.geometry("900x720")
    win.resizable(False, False)

    tk.Label(win, text="CUSTOMER REGISTRATION",
             font=("Arial", 22, "bold")).pack(pady=18)

    frame = tk.Frame(win)
    frame.pack()

    entries = {}
    labels = ["Customer Name", "Mobile Number", "Email",
              "Address", "Vehicle Number"]

    for i, label in enumerate(labels):
        tk.Label(frame, text=label, font=("Arial", 12)).grid(
            row=i, column=0, padx=12, pady=7, sticky="w")
        e = tk.Entry(frame, font=("Arial", 12), width=32)
        e.grid(row=i, column=1, padx=12, pady=7)
        entries[label] = e

    tk.Label(frame, text="Vehicle Type",
             font=("Arial", 12)).grid(row=5, column=0, padx=12, pady=7)
    vtype = ttk.Combobox(frame, values=["Car", "Bike", "Bus", "Truck"],
                         state="readonly", width=30)
    vtype.current(0)
    vtype.grid(row=5, column=1, padx=12, pady=7)

    columns = ("ID", "Name", "Mobile", "Email", "Address", "Vehicle", "Type")
    table = ttk.Treeview(win, columns=columns, show="headings", height=8)
    for c in columns:
        table.heading(c, text=c)
        table.column(c, width=115)
    table.pack(padx=10, pady=15)

    def load():
        for item in table.get_children():
            table.delete(item)
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
        messagebox.showinfo("Success", "Customer registered successfully.")
        clear()
        load()

    bf = tk.Frame(win)
    bf.pack()
    tk.Button(bf, text="Save Customer", width=18,
              font=("Arial", 11, "bold"), command=save).grid(row=0, column=0, padx=7)
    tk.Button(bf, text="Clear", width=18, command=clear).grid(row=0, column=1, padx=7)
    tk.Button(bf, text="Close", width=18, command=win.destroy).grid(row=0, column=2, padx=7)
    load()


# =========================================================
# 3. VEHICLE REGISTRATION
# =========================================================

def vehicle_registration():
    win = tk.Toplevel(root)
    win.title("Vehicle Registration")
    win.geometry("760x700")
    win.resizable(False, False)

    tk.Label(win, text="VEHICLE REGISTRATION",
             font=("Arial", 22, "bold")).pack(pady=20)

    frame = tk.Frame(win)
    frame.pack()

    def add_row(row, label):
        tk.Label(frame, text=label, font=("Arial", 12)).grid(
            row=row, column=0, padx=15, pady=7)
        e = tk.Entry(frame, font=("Arial", 12), width=34)
        e.grid(row=row, column=1, padx=15, pady=7)
        return e

    owner = add_row(0, "Owner Name")
    number = add_row(1, "Vehicle Number")
    mobile = add_row(2, "Mobile Number")

    tk.Label(frame, text="Vehicle Type",
             font=("Arial", 12)).grid(row=3, column=0, padx=15, pady=7)
    vtype = ttk.Combobox(frame, values=["Car", "Bike", "Bus", "Truck"],
                         state="readonly", width=32)
    vtype.current(0)
    vtype.grid(row=3, column=1, padx=15, pady=7)

    tk.Label(frame, text="Parking Slot",
             font=("Arial", 12)).grid(row=4, column=0, padx=15, pady=7)
    slot = ttk.Combobox(frame, values=SLOTS, state="readonly", width=32)
    slot.grid(row=4, column=1, padx=15, pady=7)

    columns = ("Owner", "Vehicle No", "Mobile", "Type", "Slot")
    table = ttk.Treeview(win, columns=columns, show="headings", height=7)
    for c in columns:
        table.heading(c, text=c)
        table.column(c, width=135)
    table.pack(pady=15)

    def load():
        for item in table.get_children():
            table.delete(item)
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
            messagebox.showinfo("Success", "Vehicle registered successfully.")
            clear_entries([owner, number, mobile])
            vtype.current(0)
            slot.set("")
            load()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Vehicle number already registered.")

    bf = tk.Frame(win)
    bf.pack()
    tk.Button(bf, text="Save Vehicle", width=20,
              font=("Arial", 11, "bold"), command=save).grid(row=0, column=0, padx=8)
    tk.Button(bf, text="Close", width=20,
              command=win.destroy).grid(row=0, column=1, padx=8)
    load()


# =========================================================
# 4. PARKING SLOT MANAGEMENT
# =========================================================

def parking_slot_management():
    win = tk.Toplevel(root)
    win.title("Parking Slot Management")
    win.geometry("820x680")
    win.resizable(False, False)

    tk.Label(win, text="PARKING SLOT MANAGEMENT",
             font=("Arial", 22, "bold")).pack(pady=18)

    info = tk.Label(win, font=("Arial", 14, "bold"))
    info.pack(pady=5)

    frame = tk.Frame(win)
    frame.pack(pady=15)
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
                                  bg="red", fg="white")
            else:
                buttons[s].config(text=f"{s}\nAVAILABLE",
                                  bg="green", fg="white")
        info.config(text=f"Available: {20-occupied}    Occupied: {occupied}")

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
        b = tk.Button(frame, text=f"{s}\nAVAILABLE",
                      width=14, height=4, font=("Arial", 11, "bold"),
                      bg="green", fg="white", command=lambda x=s: select(x))
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

    bf = tk.Frame(win)
    bf.pack(pady=15)
    tk.Button(bf, text="Refresh", width=18,
              font=("Arial", 11, "bold"), command=refresh).grid(row=0, column=0, padx=8)
    tk.Button(bf, text="Release Slot", width=18,
              font=("Arial", 11, "bold"), command=release).grid(row=0, column=1, padx=8)
    tk.Button(bf, text="Close", width=18, command=win.destroy).grid(row=0, column=2, padx=8)
    refresh()


# =========================================================
# 5. VEHICLE SEARCH
# =========================================================

def vehicle_search():
    win = tk.Toplevel(root)
    win.title("Vehicle Search / Find Vehicle")
    win.geometry("700x620")
    win.resizable(False, False)

    tk.Label(win, text="VEHICLE SEARCH / FIND VEHICLE",
             font=("Arial", 21, "bold")).pack(pady=25)

    tk.Label(win, text="Vehicle Number",
             font=("Arial", 12)).pack()
    search = tk.Entry(win, font=("Arial", 13), width=32)
    search.pack(pady=8)

    details = {}
    box = tk.LabelFrame(win, text="Vehicle Details",
                        font=("Arial", 12, "bold"), padx=20, pady=15)
    box.pack(padx=30, pady=15)

    for i, label in enumerate(["Owner Name", "Mobile Number", "Vehicle Type", "Parking Slot"]):
        tk.Label(box, text=label, font=("Arial", 12)).grid(
            row=i, column=0, padx=10, pady=10, sticky="w")
        e = tk.Entry(box, font=("Arial", 12), width=32)
        e.config(state="readonly")
        e.grid(row=i, column=1, padx=10, pady=10)
        details[label] = e

    result = tk.Label(win, text="Enter vehicle number and search.",
                      font=("Arial", 11))
    result.pack(pady=8)

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
            result.config(text="Vehicle found successfully.")
        else:
            for e in details.values():
                set_value(e, "")
            result.config(text="Vehicle not found.")
            messagebox.showerror("Not Found", "This vehicle is not registered.")

    def clear():
        search.delete(0, tk.END)
        for e in details.values():
            set_value(e, "")
        result.config(text="Enter vehicle number and search.")

    bf = tk.Frame(win)
    bf.pack(pady=15)
    tk.Button(bf, text="Search Vehicle", width=18,
              font=("Arial", 11, "bold"), command=search_vehicle).grid(row=0, column=0, padx=8)
    tk.Button(bf, text="Clear", width=18, command=clear).grid(row=0, column=1, padx=8)
    tk.Button(win, text="Close", width=20, command=win.destroy).pack(pady=10)


# =========================================================
# 6. PARKING ENTRY / EXIT
# =========================================================

def parking_entry_exit():
    win = tk.Toplevel(root)
    win.title("Parking Entry / Exit")
    win.geometry("760x650")
    win.resizable(False, False)

    tk.Label(win, text="PARKING ENTRY / EXIT",
             font=("Arial", 22, "bold")).pack(pady=20)

    frame = tk.Frame(win)
    frame.pack()

    tk.Label(frame, text="Vehicle Number", font=("Arial", 12)).grid(row=0, column=0, padx=12, pady=8)
    vehicle = tk.Entry(frame, font=("Arial", 12), width=30)
    vehicle.grid(row=0, column=1, padx=12, pady=8)

    tk.Label(frame, text="Owner Name", font=("Arial", 12)).grid(row=1, column=0, padx=12, pady=8)
    owner = tk.Entry(frame, font=("Arial", 12), width=30)
    owner.grid(row=1, column=1, padx=12, pady=8)

    tk.Label(frame, text="Parking Slot", font=("Arial", 12)).grid(row=2, column=0, padx=12, pady=8)
    slot = ttk.Combobox(frame, values=SLOTS, state="readonly", width=28)
    slot.grid(row=2, column=1, padx=12, pady=8)

    status = tk.Label(win, text="Status: Ready", font=("Arial", 13, "bold"))
    status.pack(pady=15)

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
        vehicle.delete(0, tk.END); vehicle.insert(0, n)
        owner.delete(0, tk.END); owner.insert(0, row[0])
        slot.set(row[1])
        status.config(text=f"Registered: {n} | Slot: {row[1]}")

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
        if sd and sd[0] == "Occupied":
            conn.close()
            messagebox.showerror("Slot Occupied", f"{s} is occupied by {sd[1] or 'another vehicle'}.")
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
        conn.commit(); conn.close()
        status.config(text=f"Status: IN | {now}")
        messagebox.showinfo("Success", f"Parking entry recorded.\nSlot: {s}\nEntry: {now}")

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
        conn.commit(); conn.close()
        owner.delete(0, tk.END); owner.insert(0, o)
        slot.set(s)
        status.config(text=f"Status: OUT | {exit_time}")
        messagebox.showinfo("Success",
                            f"Vehicle: {n}\nSlot: {s}\nDuration: {duration:.2f} hours")

    def clear():
        vehicle.delete(0, tk.END); owner.delete(0, tk.END); slot.set("")
        status.config(text="Status: Ready")

    bf = tk.Frame(win); bf.pack(pady=15)
    for i, (text, cmd) in enumerate([
        ("Find Vehicle", find), ("Process Entry", entry),
        ("Process Exit", exit_vehicle), ("Clear", clear)
    ]):
        tk.Button(bf, text=text, width=17,
                  font=("Arial", 11, "bold") if "Process" in text else ("Arial", 11),
                  command=cmd).grid(row=0, column=i, padx=4)
    tk.Button(win, text="Close", width=20, command=win.destroy).pack(pady=10)


# =========================================================
# 7. AI PARKING DETECTION
# =========================================================

def parking_detection():
    if not AI_AVAILABLE:
        messagebox.showerror("AI Error",
                             "OpenCV/Ultralytics is not installed. Install them first.")
        return

    win = tk.Toplevel(root)
    win.title("AI Smart Parking Detection")
    win.geometry("900x700")
    win.resizable(False, False)

    tk.Label(win, text="AI SMART PARKING DETECTION",
             font=("Arial", 22, "bold")).pack(pady=12)
    info = tk.Label(win, text="Available: 20    Occupied: 0",
                    font=("Arial", 14, "bold"))
    info.pack()
    video = tk.Label(win)
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
        win.destroy()

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
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),3)
                cv2.putText(frame,f"{s} OCCUPIED",(x1,y1+23),
                            cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,255),2)
                cur.execute("UPDATE parking_status SET status='Occupied', vehicle_number=NULL WHERE parking_slot=?", (s,))
            else:
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
                cv2.putText(frame,f"{s} AVAILABLE",(x1,y1+23),
                            cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,0),2)
                cur.execute("UPDATE parking_status SET status='Available', vehicle_number=NULL WHERE parking_slot=?", (s,))

        conn.commit(); conn.close()
        info.config(text=f"Available: {20-occupied}    Occupied: {occupied}")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ok, encoded = cv2.imencode(".png", rgb)
        if ok:
            image = tk.PhotoImage(data=encoded.tobytes())
            video.config(image=image)
            video.image = image
        win.after(40, update)

    tk.Button(win, text="Close", width=20,
              font=("Arial", 11, "bold"), command=close).pack(pady=8)
    win.protocol("WM_DELETE_WINDOW", close)
    update()


# =========================================================
# 8. PARKING HISTORY
# =========================================================

def parking_history():
    win = tk.Toplevel(root)
    win.title("Parking History")
    win.geometry("1100x600")
    win.resizable(False, False)

    tk.Label(win, text="PARKING HISTORY",
             font=("Arial", 22, "bold")).pack(pady=15)

    columns = ("ID","Vehicle","Owner","Slot","Entry","Exit","Duration","Status")
    table = ttk.Treeview(win, columns=columns, show="headings", height=18)
    widths = [50,120,130,70,150,150,90,80]
    for c,w in zip(columns,widths):
        table.heading(c,text=c); table.column(c,width=w)
    table.pack(padx=10,pady=10)

    conn = db_connect(); cur = conn.cursor()
    cur.execute("""
        SELECT id, vehicle_number, owner, parking_slot,
               entry_time, COALESCE(exit_time,''), 
               COALESCE(ROUND(duration_hours,2),0), status
        FROM parking_transactions ORDER BY id DESC
    """)
    for row in cur.fetchall():
        table.insert("", "end", values=row)
    conn.close()

    tk.Button(win,text="Close",width=20,command=win.destroy).pack(pady=8)


# =========================================================
# 9. PAYMENT / BILLING
# =========================================================

def payment_billing():
    win = tk.Toplevel(root)
    win.title("Payment / Billing")
    win.geometry("700x650")
    win.resizable(False, False)

    tk.Label(win,text="PARKING PAYMENT / BILLING",
             font=("Arial",22,"bold")).pack(pady=20)

    frame=tk.Frame(win); frame.pack()
    tk.Label(frame,text="Vehicle Number",font=("Arial",12)).grid(row=0,column=0,padx=12,pady=8)
    vehicle=tk.Entry(frame,font=("Arial",12),width=30); vehicle.grid(row=0,column=1,padx=12,pady=8)
    tk.Label(frame,text="Owner Name",font=("Arial",12)).grid(row=1,column=0,padx=12,pady=8)
    owner=tk.Entry(frame,font=("Arial",12),width=30); owner.grid(row=1,column=1,padx=12,pady=8)
    tk.Label(frame,text="Parking Slot",font=("Arial",12)).grid(row=2,column=0,padx=12,pady=8)
    slot=tk.Entry(frame,font=("Arial",12),width=30); slot.grid(row=2,column=1,padx=12,pady=8)
    tk.Label(frame,text="Duration (Hours)",font=("Arial",12)).grid(row=3,column=0,padx=12,pady=8)
    duration=tk.Entry(frame,font=("Arial",12),width=30); duration.grid(row=3,column=1,padx=12,pady=8)
    tk.Label(frame,text="Rate Per Hour (₹)",font=("Arial",12)).grid(row=4,column=0,padx=12,pady=8)
    rate=tk.Entry(frame,font=("Arial",12),width=30); rate.insert(0,"20"); rate.grid(row=4,column=1,padx=12,pady=8)
    tk.Label(frame,text="Payment Mode",font=("Arial",12)).grid(row=5,column=0,padx=12,pady=8)
    mode=ttk.Combobox(frame,values=["Cash","UPI","Card"],state="readonly",width=28)
    mode.current(0); mode.grid(row=5,column=1,padx=12,pady=8)

    total=tk.Label(win,text="Total Amount: ₹0.00",font=("Arial",16,"bold"))
    total.pack(pady=18)

    def find():
        n=vehicle.get().strip().upper()
        if not n:
            messagebox.showwarning("Warning","Enter vehicle number."); return
        conn=db_connect(); cur=conn.cursor()
        cur.execute("SELECT owner,parking_slot FROM vehicles WHERE UPPER(vehicle_number)=?",(n,))
        row=cur.fetchone(); conn.close()
        if row:
            owner.delete(0,tk.END); owner.insert(0,row[0])
            slot.delete(0,tk.END); slot.insert(0,row[1])
        else:
            messagebox.showerror("Not Found","Vehicle is not registered.")

    def bill():
        try:
            d=float(duration.get()); r=float(rate.get())
            if d<=0 or r<=0: raise ValueError
        except ValueError:
            messagebox.showerror("Error","Duration and rate must be positive numbers."); return
        n,o,s=vehicle.get().strip().upper(),owner.get().strip(),slot.get().strip()
        if not all([n,o,s]):
            messagebox.showwarning("Warning","Please fill vehicle details."); return
        amount=d*r
        total.config(text=f"Total Amount: ₹{amount:.2f}")
        conn=db_connect(); cur=conn.cursor()
        cur.execute("""
            INSERT INTO payments
            (vehicle_number,owner,parking_slot,duration_hours,rate_per_hour,total_amount,payment_mode,payment_time)
            VALUES (?,?,?,?,?,?,?,?)
        """,(n,o,s,d,r,amount,mode.get(),datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
        messagebox.showinfo("Payment Successful",f"Vehicle: {n}\nAmount: ₹{amount:.2f}\nMode: {mode.get()}")

    bf=tk.Frame(win); bf.pack(pady=8)
    tk.Button(bf,text="Find Vehicle",width=18,command=find).grid(row=0,column=0,padx=8)
    tk.Button(bf,text="Generate Bill",width=18,font=("Arial",11,"bold"),command=bill).grid(row=0,column=1,padx=8)
    tk.Button(win,text="Close",width=20,command=win.destroy).pack(pady=10)


# =========================================================
# 10. PAYMENT HISTORY / REPORT
# =========================================================

def payment_history():
    win=tk.Toplevel(root); win.title("Payment History"); win.geometry("1000x560"); win.resizable(False,False)
    tk.Label(win,text="PAYMENT HISTORY / REPORT",font=("Arial",22,"bold")).pack(pady=18)
    columns=("ID","Vehicle","Owner","Slot","Hours","Rate","Amount","Mode","Date")
    table=ttk.Treeview(win,columns=columns,show="headings",height=17)
    for c in columns:
        table.heading(c,text=c); table.column(c,width=105)
    table.pack(padx=10,pady=10)
    conn=db_connect(); cur=conn.cursor()
    cur.execute("""SELECT id,vehicle_number,owner,parking_slot,duration_hours,rate_per_hour,total_amount,payment_mode,payment_time FROM payments ORDER BY id DESC""")
    for row in cur.fetchall(): table.insert("", "end", values=row)
    conn.close()
    tk.Button(win,text="Close",width=20,command=win.destroy).pack(pady=8)


# =========================================================
# 11. FEEDBACK
# =========================================================

def feedback_form():
    win=tk.Toplevel(root); win.title("Customer Feedback"); win.geometry("650x560"); win.resizable(False,False)
    tk.Label(win,text="CUSTOMER FEEDBACK",font=("Arial",22,"bold")).pack(pady=25)
    frame=tk.Frame(win); frame.pack(pady=10)
    tk.Label(frame,text="Name",font=("Arial",12)).grid(row=0,column=0,padx=15,pady=10)
    name=tk.Entry(frame,font=("Arial",12),width=32); name.grid(row=0,column=1,padx=15,pady=10)
    tk.Label(frame,text="Rating",font=("Arial",12)).grid(row=1,column=0,padx=15,pady=10)
    rating=ttk.Combobox(frame,values=["Excellent","Very Good","Good","Average","Poor"],state="readonly",width=30)
    rating.current(0); rating.grid(row=1,column=1,padx=15,pady=10)
    tk.Label(frame,text="Comments",font=("Arial",12)).grid(row=2,column=0,padx=15,pady=10,sticky="n")
    comments=tk.Text(frame,width=32,height=7,font=("Arial",11)); comments.grid(row=2,column=1,padx=15,pady=10)
    def save():
        n=name.get().strip(); c=comments.get("1.0",tk.END).strip()
        if not n: messagebox.showwarning("Warning","Enter your name."); return
        conn=db_connect(); cur=conn.cursor()
        cur.execute("INSERT INTO feedback(name,rating,comments,feedback_time) VALUES(?,?,?,?)",
                    (n,rating.get(),c,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
        messagebox.showinfo("Thank You","Feedback submitted successfully.")
        name.delete(0,tk.END); comments.delete("1.0",tk.END)
    tk.Button(win,text="Submit Feedback",width=22,font=("Arial",12,"bold"),command=save).pack(pady=15)
    tk.Button(win,text="Close",width=22,command=win.destroy).pack()


# =========================================================
# 12. PARKING REPORT
# =========================================================

def parking_report():
    win=tk.Toplevel(root); win.title("Parking Report"); win.geometry("700x520"); win.resizable(False,False)
    tk.Label(win,text="PARKING REPORT",font=("Arial",22,"bold")).pack(pady=25)
    box=tk.Frame(win); box.pack(pady=15)
    data=get_slot_data()
    occupied=sum(1 for s in SLOTS if data.get(s,("Available",None))[0]=="Occupied")
    conn=db_connect(); cur=conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vehicles"); vehicles=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM parking_transactions WHERE status='IN'"); active=cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(total_amount),0) FROM payments"); revenue=cur.fetchone()[0]
    conn.close()
    stats=[
        ("Total Parking Slots","20"),
        ("Available Slots",str(20-occupied)),
        ("Occupied Slots",str(occupied)),
        ("Registered Vehicles",str(vehicles)),
        ("Active Entries",str(active)),
        ("Total Revenue",f"₹{revenue:.2f}")
    ]
    for i,(a,b) in enumerate(stats):
        tk.Label(box,text=a,font=("Arial",13,"bold")).grid(row=i,column=0,padx=30,pady=10,sticky="w")
        tk.Label(box,text=b,font=("Arial",13)).grid(row=i,column=1,padx=30,pady=10)
    tk.Button(win,text="Close",width=20,command=win.destroy).pack(pady=20)


# =========================================================
# 13. NOTIFICATIONS / STATUS
# =========================================================

def notifications():
    win=tk.Toplevel(root); win.title("Notifications"); win.geometry("650x500"); win.resizable(False,False)
    tk.Label(win,text="SYSTEM NOTIFICATIONS",font=("Arial",22,"bold")).pack(pady=25)
    data=get_slot_data()
    occupied=[s for s in SLOTS if data.get(s,("Available",None))[0]=="Occupied"]
    messages=[
        f"System is running normally.",
        f"Total slots: 20",
        f"Occupied slots: {len(occupied)}",
        f"Available slots: {20-len(occupied)}",
        f"Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    for m in messages:
        tk.Label(win,text="• "+m,font=("Arial",12),anchor="w").pack(padx=50,pady=9,fill="x")
    tk.Button(win,text="Close",width=20,command=win.destroy).pack(pady=20)


# =========================================================
# 14. SETTINGS
# =========================================================

def settings():
    win=tk.Toplevel(root); win.title("System Settings"); win.geometry("650x520"); win.resizable(False,False)
    tk.Label(win,text="SYSTEM SETTINGS",font=("Arial",22,"bold")).pack(pady=25)
    frame=tk.Frame(win); frame.pack(pady=15)
    tk.Label(frame,text="Parking Rate Per Hour (₹)",font=("Arial",12)).grid(row=0,column=0,padx=15,pady=12)
    rate=tk.Entry(frame,font=("Arial",12),width=25); rate.insert(0,"20"); rate.grid(row=0,column=1,padx=15,pady=12)
    tk.Label(frame,text="Total Parking Slots",font=("Arial",12)).grid(row=1,column=0,padx=15,pady=12)
    total=tk.Entry(frame,font=("Arial",12),width=25); total.insert(0,"20"); total.config(state="readonly"); total.grid(row=1,column=1,padx=15,pady=12)
    tk.Label(frame,text="Vehicle Types",font=("Arial",12)).grid(row=2,column=0,padx=15,pady=12)
    types=tk.Entry(frame,font=("Arial",12),width=25); types.insert(0,"Car, Bike, Bus, Truck"); types.config(state="readonly"); types.grid(row=2,column=1,padx=15,pady=12)
    def save():
        try:
            if float(rate.get())<=0: raise ValueError
        except ValueError:
            messagebox.showerror("Error","Enter a valid positive rate."); return
        messagebox.showinfo("Saved","Settings saved successfully.")
    tk.Button(win,text="Save Settings",width=20,font=("Arial",12,"bold"),command=save).pack(pady=25)
    tk.Button(win,text="Close",width=20,command=win.destroy).pack()


# =========================================================
# 15. HELP / ABOUT
# =========================================================

def help_about():
    win=tk.Toplevel(root); win.title("Help / About Project"); win.geometry("700x600"); win.resizable(False,False)
    tk.Label(win,text="SMART PARKING DETECTION",font=("Arial",22,"bold")).pack(pady=25)
    text=(
        "Project: Smart Parking Detection\n\n"
        "This system provides:\n"
        "• Customer and vehicle registration\n"
        "• Parking slot management\n"
        "• Vehicle search\n"
        "• Parking entry and exit\n"
        "• AI vehicle detection using YOLO\n"
        "• Parking history\n"
        "• Payment and billing\n"
        "• Reports and feedback\n"
        "• System settings and notifications\n\n"
        "Login: admin\n"
        "Password: admin123"
    )
    tk.Label(win,text=text,font=("Arial",12),justify="left").pack(padx=40,pady=15,anchor="w")
    tk.Button(win,text="Close",width=20,command=win.destroy).pack(pady=20)


# =========================================================
# LOGOUT
# =========================================================

def logout(dashboard):
    dashboard.destroy()
    root.deiconify()
    username_entry.delete(0,tk.END)
    password_entry.delete(0,tk.END)


# =========================================================
# DASHBOARD
# =========================================================

def open_dashboard():
    dashboard=tk.Toplevel(root)
    dashboard.title("Smart Parking Detection - Dashboard")
    dashboard.geometry("900x760")
    dashboard.resizable(False,False)

    tk.Label(dashboard,text="SMART PARKING DETECTION",
             font=("Arial",24,"bold")).pack(pady=20)

    frame=tk.Frame(dashboard)
    frame.pack(pady=5)

    buttons=[
        ("Admin Profile",admin_profile),
        ("Customer Registration",customer_registration),
        ("Vehicle Registration",vehicle_registration),
        ("Parking Slot Management",parking_slot_management),
        ("Vehicle Search / Find Vehicle",vehicle_search),
        ("Parking Entry / Exit",parking_entry_exit),
        ("AI Parking Detection",parking_detection),
        ("Parking History",parking_history),
        ("Payment / Billing",payment_billing),
        ("Payment History / Report",payment_history),
        ("Parking Report",parking_report),
        ("Customer Feedback",feedback_form),
        ("Notifications / Status",notifications),
        ("System Settings",settings),
        ("Help / About",help_about)
    ]

    for i,(text,cmd) in enumerate(buttons):
        tk.Button(frame,text=text,font=("Arial",11),
                  width=28,height=1,command=cmd).grid(
                      row=i//3,column=i%3,padx=10,pady=7)

    bottom=tk.Frame(dashboard); bottom.pack(pady=15)
    tk.Button(bottom,text="Logout",font=("Arial",11,"bold"),
              width=18,command=lambda:logout(dashboard)).grid(row=0,column=0,padx=10)
    tk.Button(bottom,text="Exit",font=("Arial",11,"bold"),
              width=18,command=root.destroy).grid(row=0,column=1,padx=10)

    dashboard.protocol("WM_DELETE_WINDOW",lambda:logout(dashboard))


# =========================================================
# LOGIN
# =========================================================

def login():
    username=username_entry.get().strip()
    password=password_entry.get().strip()

    if username=="" or password=="":
        messagebox.showwarning("Warning","Please enter username and password.")
        return

    if username=="admin" and password=="admin123":
        messagebox.showinfo("Login Successful","Welcome to Smart Parking Detection")
        root.withdraw()
        open_dashboard()
    else:
        messagebox.showerror("Login Failed","Invalid username or password.")


# =========================================================
# MAIN
# =========================================================

create_database()

root=tk.Tk()
root.title("Smart Parking Detection")
root.geometry("600x500")
root.resizable(False,False)

tk.Label(root,text="SMART PARKING DETECTION",
         font=("Arial",24,"bold")).pack(pady=55)

tk.Label(root,text="Username",font=("Arial",13)).pack()
username_entry=tk.Entry(root,font=("Arial",13),width=30)
username_entry.pack(pady=10)

tk.Label(root,text="Password",font=("Arial",13)).pack()
password_entry=tk.Entry(root,font=("Arial",13),width=30,show="*")
password_entry.pack(pady=10)

tk.Button(root,text="LOGIN",font=("Arial",13,"bold"),
          width=20,command=login).pack(pady=25)

tk.Button(root,text="EXIT",font=("Arial",12),
          width=20,command=root.destroy).pack()

root.mainloop()
