import streamlit as st
import sqlite3
import os
from PIL import Image
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import datetime

# --- Constants & Setup ---
DB_FILE = "data/pos.db"
BARCODE_DIR = "assets/barcodes"
IMAGE_DIR = "assets/images"
FONT_DIR = "assets/fonts"
SETTINGS_FILE = "data/settings.txt"

os.makedirs("data", exist_ok=True)
os.makedirs(BARCODE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

st.set_page_config(page_title="Quantum POS", layout="wide")

# --- Init DB ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            quantity INTEGER,
            barcode TEXT UNIQUE,
            image_path TEXT
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            items TEXT,
            total REAL,
            date TEXT
        )""")
init_db()

# --- Settings Load ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            lines = f.readlines()
            return lines[0].strip(), lines[1].strip() if len(lines) >= 2 else ("Quantum POS", "Invoice")
    return "Quantum POS", "Invoice"

# --- Settings Save ---
def save_settings(system_name, invoice_title):
    with open(SETTINGS_FILE, "w") as f:
        f.write(f"{system_name}\n{invoice_title}")

# --- Inject Font ---
def inject_font(font_file):
    if font_file:
        font_path = os.path.join(FONT_DIR, font_file.name)
        with open(font_path, "wb") as f:
            f.write(font_file.read())
        st.markdown(
            f"""
            <style>
            @font-face {{
                font-family: 'custom';
                src: url('/assets/fonts/{font_file.name}');
            }}
            html, body, [class*="css"] {{
                font-family: 'custom', sans-serif;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

# --- Add Product ---
def add_product(name, price, quantity, barcode_value, image_file):
    barcode_path = os.path.join(BARCODE_DIR, f"{barcode_value}.png")
    image_path = None

    barcode_img = barcode.get('code128', barcode_value, writer=ImageWriter())
    barcode_img.save(barcode_path)

    if image_file:
        image_path = os.path.join(IMAGE_DIR, image_file.name)
        with open(image_path, "wb") as f:
            f.write(image_file.read())

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO products (name, price, quantity, barcode, image_path) VALUES (?, ?, ?, ?, ?)",
                     (name, price, quantity, barcode_value, image_path))
        conn.commit()

# --- Get Products ---
def get_products(search=""):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        if search:
            cur.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{search}%", f"%{search}%"))
        else:
            cur.execute("SELECT * FROM products")
        return cur.fetchall()

# --- Get Product by Barcode ---
def get_product_by_barcode(code):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE barcode = ?", (code,))
        return cur.fetchone()

# --- Update Stock ---
def update_stock(product_id, quantity_change):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity_change, product_id))
        conn.commit()

# --- Save Sale ---
def save_sale(cart, total):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO sales (items, total, date) VALUES (?, ?, ?)",
                     (str(cart), total, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

# --- Draw Invoice Text (Simulated) ---
def generate_invoice(cart, total, received):
    system_name, invoice_title = load_settings()
    lines = [f"{system_name} - {invoice_title}", "-" * 32]
    for item in cart:
        name = item['name'][:12]
        qty = item['qty']
        price = item['price']
        lines.append(f"{name:<12} x{qty:<3} ${price * qty:>6.2f}")
    lines.append("-" * 32)
    lines.append(f"Total:     ${total:.2f}")
    lines.append(f"Received:  ${received:.2f}")
    lines.append(f"Change:    ${received - total:.2f}")
    lines.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("-" * 32)
    return "\n".join(lines)

# --- UI Start ---
system_name, invoice_title = load_settings()
st.sidebar.title(system_name)
page = st.sidebar.radio("📂 Menu", ["🛒 POS", "📦 Inventory", "⚙️ Settings"])

# --- POS Page ---
if page == "🛒 POS":
    st.title("🛒 Point of Sale")
    if "cart" not in st.session_state:
        st.session_state.cart = []

    st.text_input("🔍 Scan or Enter Barcode", key="barcode_input")
    if st.session_state.barcode_input:
        product = get_product_by_barcode(st.session_state.barcode_input.strip())
        if product:
            for item in st.session_state.cart:
                if item["id"] == product[0]:
                    item["qty"] += 1
                    break
            else:
                st.session_state.cart.append({
                    "id": product[0],
                    "name": product[1],
                    "price": product[2],
                    "qty": 1
                })
        st.session_state.barcode_input = ""

    products = get_products()
    st.subheader("🧾 Product Menu")
    for p in products:
        if st.button(f"{p[1]} - ${p[2]}", key=f"add_{p[0]}"):
            for item in st.session_state.cart:
                if item["id"] == p[0]:
                    item["qty"] += 1
                    break
            else:
                st.session_state.cart.append({
                    "id": p[0],
                    "name": p[1],
                    "price": p[2],
                    "qty": 1
                })

    st.subheader("🛒 Cart")
    total = sum(item["qty"] * item["price"] for item in st.session_state.cart)
    for item in st.session_state.cart:
        st.write(f"{item['name']} x{item['qty']} = ${item['qty'] * item['price']:.2f}")
    st.write(f"**Total: ${total:.2f}**")

    received = st.number_input("💵 Amount Received", min_value=0.0, value=0.0, step=0.1)
    if st.button("✅ Checkout"):
        if received >= total:
            for item in st.session_state.cart:
                update_stock(item["id"], item["qty"])
            save_sale(st.session_state.cart, total)
            invoice = generate_invoice(st.session_state.cart, total, received)
            st.success("✅ Sale completed. Printing invoice:")
            st.code(invoice)
            st.session_state.cart = []
        else:
            st.error("❌ Received amount is less than total.")

# --- Inventory Page ---
elif page == "📦 Inventory":
    st.title("📦 Inventory")
    with st.expander("➕ Add New Product", expanded=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Name")
        price = col1.number_input("Price", min_value=0.0, format="%.2f")
        qty = col2.number_input("Quantity", min_value=0, step=1)
        barcode_value = col2.text_input("Barcode (auto if blank)")
        if not barcode_value:
            barcode_value = f"QTA{int(price*100)}{qty}"
        image_file = st.file_uploader("Product Image", type=["jpg", "png", "jpeg"])
        if st.button("Add Product"):
            try:
                add_product(name, price, qty, barcode_value, image_file)
                st.success("✅ Product added.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()
    search = st.text_input("Search Product")
    for p in get_products(search):
        cols = st.columns([3, 2, 2, 2])
        cols[0].markdown(f"**{p[1]}**")
        cols[1].markdown(f"${p[2]:.2f}")
        cols[2].markdown(f"{p[3]} in stock")
        if p[5] and os.path.exists(p[5]):
            cols[3].image(p[5], width=50)

# --- Settings Page ---
elif page == "⚙️ Settings":
    st.title("⚙️ System Settings")
    new_name = st.text_input("System Name", value=system_name)
    new_invoice = st.text_input("Invoice Title", value=invoice_title)
    font_file = st.file_uploader("Upload Custom Font (.ttf or .otf)", type=["ttf", "otf"])

    if st.button("💾 Save Settings"):
        save_settings(new_name, new_invoice)
        st.success("✅ Settings saved. Reload the page to apply font.")
        if font_file:
            inject_font(font_file)
