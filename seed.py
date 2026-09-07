"""
seed.py — Creates the SQLite database from schema.sql and inserts
realistic sample data for testing: students, an administrator, and fee
categories across all three category types (School, Departmental, Faculty).

Run with:  python seed.py
"""
import os
import sqlite3
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "sumas.sqlite")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.executescript(open(SCHEMA_PATH).read())

# --- Administrator ---
conn.execute(
    "INSERT INTO administrator (staff_id, full_name, password_hash) VALUES (?, ?, ?)",
    ("ADM/001", "Ifeoma Obi", generate_password_hash("admin123")),
)

# --- Students ---
students = [
    ("SUMAS/2022/0697", "Eze Ezekiel", "Computer Science", "Natural Sciences", "400", "student123"),
    ("SUMAS/2022/0512", "Chidinma Okafor", "Computer Science", "Natural Sciences", "400", "student123"),
    ("SUMAS/2023/0188", "Tunde Bakare", "Nursing Science", "Health Sciences", "300", "student123"),
]
for reg, name, dept, fac, level, pw in students:
    conn.execute(
        "INSERT INTO student (reg_number, full_name, department, faculty, level, password_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (reg, name, dept, fac, level, generate_password_hash(pw)),
    )

# --- Fee categories (session 2025/2026) ---
# School Fees varies by level (a NULL level would mean "every level pays
# the same", which isn't realistic for tuition); Departmental/Faculty Fees
# stay level = None ("All Levels") here to demonstrate both are supported.
session = "2025/2026"
fee_categories = [
    ("School Fees", session, "100", None, None, 180000.00),
    ("School Fees", session, "200", None, None, 150000.00),
    ("School Fees", session, "300", None, None, 150000.00),
    ("School Fees", session, "400", None, None, 150000.00),
    ("Departmental Fee", session, None, "Computer Science", None, 25000.00),
    ("Departmental Fee", session, None, "Nursing Science", None, 30000.00),
    ("Faculty Fee", session, None, None, "Natural Sciences", 10000.00),
    ("Faculty Fee", session, None, None, "Health Sciences", 12000.00),
]
for name, sess, level, dept, fac, amount in fee_categories:
    conn.execute(
        "INSERT INTO fee_category (category_name, session, level, department, faculty, amount) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, sess, level, dept, fac, amount),
    )

conn.commit()
conn.close()

print(f"Database created at {DB_PATH}")
print("Sample logins:")
print("  Admin      -> staff_id=ADM/001            password=admin123")
print("  Student 1  -> reg_number=SUMAS/2022/0697   password=student123")
print("  Student 2  -> reg_number=SUMAS/2022/0512   password=student123")
print("  Student 3  -> reg_number=SUMAS/2023/0188   password=student123")
