import streamlit as st
import sqlite3
import os
from PIL import Image
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

# --- Setup ---
st.set_page_config(page_title="Quantum POS", layout="wide")
DB_FILE = "data/pos.db"
BARCODE_DIR = "assets/barcodes"
IMAGE_DIR = "assets/images"
os.makedirs("data", exist_ok=True)
os.makedirs(BARCODE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# --- Initialize DB ---
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
        )
        """)
init_db()

# --- Add Product ---
def add_product(name, price, quantity, barcode_value, image_file):
    barcode_path = os.path.join(BARCODE_DIR, f"{barcode_value}.png")
    image_path = None

    # Generate barcode image
    barcode_img = barcode.get('code128', barcode_value, writer=ImageWriter())
    barcode_img.save(barcode_path)

    # Save uploaded product image
    if image_file:
        image_path = os.path.join(IMAGE_DIR, image_file.name)
        with open(image_path, "wb") as f:
            f.write(image_file.read())

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        INSERT INTO products (name, price, quantity, barcode, image_path)
        VALUES (?, ?, ?, ?, ?)
        """, (name, price, quantity, barcode_value, image_path))
        conn.commit()

# --- Get Products ---
def get_products(search=""):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if search:
            cursor.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", 
                           (f"%{search}%", f"%{search}%"))
        else:
            cursor.execute("SELECT * FROM products")
        return cursor.fetchall()

# --- App Sidebar Navigation ---
page = st.sidebar.selectbox("📂 Navigate", ["📦 Inventory"])

# --- Inventory Page ---
if page == "📦 Inventory":
    st.title("📦 Inventory Management")

    with st.expander("➕ Add New Product", expanded=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Product Name")
        price = col1.number_input("Price", min_value=0.0, format="%.2f")
        quantity = col2.number_input("Quantity in Stock", min_value=0, step=1)
        barcode_value = col2.text_input("Barcode (leave empty to auto-generate)")

        if not barcode_value:
            barcode_value = f"QTA{int(price*1000)}{quantity}"

        image_file = st.file_uploader("Upload Product Image", type=["png", "jpg", "jpeg"])

        if st.button("Add Product"):
            try:
                add_product(name, price, quantity, barcode_value, image_file)
                st.success("✅ Product added successfully.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()
    st.subheader("🔍 Product List")
    search = st.text_input("Search by name or barcode")
    products = get_products(search)

    if not products:
        st.warning("No products found.")
    else:
        for pid, name, price, qty, code, img in products:
            with st.container():
                cols = st.columns([3, 2, 2, 3])
                cols[0].markdown(f"**{name}**")
                cols[1].markdown(f"💲 Price: `{price:.2f}`")
                cols[2].markdown(f"📦 Stock: `{qty}`")
                if img and os.path.exists(img):
                    cols[3].image(img, width=60)
                st.markdown(f"📛 Barcode: `{code}`")
                barcode_path = os.path.join(BARCODE_DIR, f"{code}.png")
                if os.path.exists(barcode_path):
                    st.image(barcode_path, width=120)
                st.markdown("---")
