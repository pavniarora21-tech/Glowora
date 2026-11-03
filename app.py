from flask import (
    Flask, render_template, abort, request,
    redirect, url_for, session, flash
)
from functools import wraps
import os
import sqlite3
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4

# ==========================================
# FLASK CONFIGURATION
# ==========================================

app = Flask(__name__)

# Secret key is read from environment variable on the server.
# The default value is only for local development.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "glowora.db"

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ==========================================
# ADMIN LOGIN DETAILS
# ==========================================

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Glowora@123")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# ==========================================
# ADMIN LOGIN PROTECTION
# ==========================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# CUSTOMER LOGIN PROTECTION
# ==========================================

def customer_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("customer_id"):
            flash("Please login to access your account.")
            return redirect(url_for("customer_login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def initialize_database():

    connection = get_db()

    # Products table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL
        )
    """)

    # Customers table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Orders table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            pincode TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            total REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Order items table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)

    # Check existing order columns
    order_columns = connection.execute(
        "PRAGMA table_info(orders)"
    ).fetchall()

    column_names = [column["name"] for column in order_columns]

    # Add order status column if missing
    if "status" not in column_names:

        connection.execute("""
            ALTER TABLE orders
            ADD COLUMN status TEXT DEFAULT 'Pending'
        """)

    # Add customer_id column if missing
    if "customer_id" not in column_names:

        connection.execute("""
            ALTER TABLE orders
            ADD COLUMN customer_id INTEGER
        """)

    # Insert default products only if database is empty
    count = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    if count == 0:

        products = [
            (
                "Rose Glow Serum",
                "Skincare",
                599,
                "A lightweight serum for your daily skincare routine.",
                "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=600&q=80"
            ),
            (
                "Velvet Matte Lipstick",
                "Makeup",
                399,
                "A stylish lipstick to complete your everyday look.",
                "https://images.unsplash.com/photo-1586495777744-4413f21062fa?auto=format&fit=crop&w=600&q=80"
            ),
            (
                "Hydrating Face Cream",
                "Skincare",
                499,
                "A nourishing moisturizer for your beauty routine.",
                "https://images.unsplash.com/photo-1601049541289-9b1b7bbbfe19?auto=format&fit=crop&w=600&q=80"
            ),
            (
                "Signature Fragrance",
                "Fragrance",
                899,
                "An elegant fragrance for special moments.",
                "https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=600&q=80"
            ),
            (
                "Beauty Essentials Kit",
                "Self-Care",
                749,
                "A curated set of beauty essentials.",
                "https://images.unsplash.com/photo-1600612253971-422e7f7faeb6?auto=format&fit=crop&w=600&q=80"
            ),
            (
                "Daily Skin Cleanser",
                "Skincare",
                349,
                "A simple cleanser for your daily routine.",
                "https://images.unsplash.com/photo-1556229010-6c3f2c9ca5f8?auto=format&fit=crop&w=600&q=80"
            )
        ]

        connection.executemany("""
            INSERT INTO products
            (name, category, price, description, image)
            VALUES (?, ?, ?, ?, ?)
        """, products)

    connection.commit()
    connection.close()


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    connection = get_db()

    products = connection.execute("""
        SELECT * FROM products
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    cart_count = sum(session.get("cart", {}).values())

    return render_template(
        "index.html",
        products=products,
        cart_count=cart_count
    )


# ==========================================
# SHOP PAGE
# ==========================================

@app.route("/shop")
def shop():

    category = request.args.get("category", "").strip()

    connection = get_db()

    if category:

        products = connection.execute("""
            SELECT * FROM products
            WHERE category = ?
            ORDER BY id
        """, (category,)).fetchall()

    else:

        products = connection.execute("""
            SELECT * FROM products
            ORDER BY id
        """).fetchall()

    categories = connection.execute("""
        SELECT DISTINCT category
        FROM products
        ORDER BY category
    """).fetchall()

    connection.close()

    cart_count = sum(session.get("cart", {}).values())

    return render_template(
        "shop.html",
        products=products,
        categories=categories,
        selected_category=category,
        cart_count=cart_count
    )


# ==========================================
# PRODUCT DETAILS
# ==========================================

@app.route("/product/<int:product_id>")
def product_detail(product_id):

    connection = get_db()

    product = connection.execute("""
        SELECT * FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    connection.close()

    if product is None:
        abort(404)

    cart_count = sum(session.get("cart", {}).values())

    return render_template(
        "product.html",
        product=product,
        cart_count=cart_count
    )


# ==========================================
# ADD TO CART
# ==========================================

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):

    connection = get_db()

    product = connection.execute("""
        SELECT id FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    connection.close()

    if product is None:
        abort(404)

    cart = session.get("cart", {})

    product_key = str(product_id)

    cart[product_key] = cart.get(product_key, 0) + 1

    session["cart"] = cart

    return redirect(url_for("cart"))


# ==========================================
# SHOPPING CART
# ==========================================

@app.route("/cart")
def cart():

    cart_items = []
    total = 0

    cart_data = session.get("cart", {})

    connection = get_db()

    for product_id, quantity in cart_data.items():

        product = connection.execute("""
            SELECT * FROM products
            WHERE id = ?
        """, (int(product_id),)).fetchone()

        if product and quantity > 0:

            subtotal = product["price"] * quantity

            total += subtotal

            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })

    connection.close()

    cart_count = sum(cart_data.values())

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total,
        cart_count=cart_count
    )


# ==========================================
# UPDATE CART QUANTITY
# ==========================================

@app.route("/update-cart/<int:product_id>", methods=["POST"])
def update_cart(product_id):

    cart = session.get("cart", {})
    product_key = str(product_id)

    if product_key in cart:

        action = request.form.get("action")

        quantity = int(cart[product_key])

        if action == "increase":
            quantity += 1

        elif action == "decrease":
            quantity = max(1, quantity - 1)

        cart[product_key] = quantity

        session["cart"] = cart

    return redirect(url_for("cart"))


# ==========================================
# REMOVE FROM CART
# ==========================================

@app.route("/remove-from-cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):

    cart = session.get("cart", {})

    cart.pop(str(product_id), None)

    session["cart"] = cart

    return redirect(url_for("cart"))


# ==========================================
# CLEAR CART
# ==========================================

@app.route("/clear-cart", methods=["POST"])
def clear_cart():

    session["cart"] = {}

    return redirect(url_for("cart"))


# ==========================================
# CHECKOUT
# ==========================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart_data = session.get("cart", {})

    if not cart_data:

        flash("Your cart is empty. Please add products first.")

        return redirect(url_for("shop"))

    cart_items = []
    total = 0

    connection = get_db()

    for product_id, quantity in cart_data.items():

        product = connection.execute("""
            SELECT * FROM products
            WHERE id = ?
        """, (int(product_id),)).fetchone()

        if product and quantity > 0:

            subtotal = product["price"] * quantity

            total += subtotal

            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })

    if not cart_items:

        connection.close()

        session["cart"] = {}

        return redirect(url_for("shop"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        phone = request.form.get(
            "phone", ""
        ).strip()

        address = request.form.get(
            "address", ""
        ).strip()

        city = request.form.get(
            "city", ""
        ).strip()

        pincode = request.form.get(
            "pincode", ""
        ).strip()

        payment_method = request.form.get(
            "payment_method", ""
        )

        if not all([
            full_name,
            email,
            phone,
            address,
            city,
            pincode
        ]):

            connection.close()

            flash("Please fill in all delivery details.")

            return redirect(url_for("checkout"))

        if (
            len(phone) != 10
            or not phone.isdigit()
            or len(pincode) != 6
            or not pincode.isdigit()
        ):

            connection.close()

            flash(
                "Please enter a valid 10-digit phone number "
                "and 6-digit PIN code."
            )

            return redirect(url_for("checkout"))

        if payment_method != "Cash on Delivery":

            connection.close()

            flash("Please select Cash on Delivery.")

            return redirect(url_for("checkout"))

        # Associate order with logged-in customer, if available
        customer_id = session.get("customer_id")

        cursor = connection.execute("""
            INSERT INTO orders (
                full_name,
                email,
                phone,
                address,
                city,
                pincode,
                payment_method,
                total,
                customer_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_name,
            email,
            phone,
            address,
            city,
            pincode,
            payment_method,
            total,
            customer_id
        ))

        order_id = cursor.lastrowid

        for item in cart_items:

            connection.execute("""
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    product_name,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                item["product"]["id"],
                item["product"]["name"],
                item["quantity"],
                item["product"]["price"],
                item["subtotal"]
            ))

        connection.commit()
        connection.close()

        session["cart"] = {}

        return redirect(
            url_for("order_success", order_id=order_id)
        )

    connection.close()

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )


# ==========================================
# ORDER SUCCESS PAGE
# ==========================================

@app.route("/order-success/<int:order_id>")
def order_success(order_id):

    connection = get_db()

    order = connection.execute("""
        SELECT * FROM orders
        WHERE id = ?
    """, (order_id,)).fetchone()

    if order is None:
        connection.close()
        abort(404)

    items = connection.execute("""
        SELECT * FROM order_items
        WHERE order_id = ?
    """, (order_id,)).fetchall()

    connection.close()

    return render_template(
        "order_success.html",
        order=order,
        items=items
    )


# ==========================================
# CUSTOMER REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def customer_register():

    if session.get("customer_id"):
        return redirect(url_for("customer_account"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        phone = request.form.get(
            "phone", ""
        ).strip()

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([
            full_name,
            email,
            phone,
            password,
            confirm_password
        ]):

            flash("Please fill in all fields.")
            return redirect(url_for("customer_register"))

        if len(phone) != 10 or not phone.isdigit():

            flash("Please enter a valid 10-digit phone number.")
            return redirect(url_for("customer_register"))

        if len(password) < 8:

            flash("Password must contain at least 8 characters.")
            return redirect(url_for("customer_register"))

        if password != confirm_password:

            flash("Passwords do not match.")
            return redirect(url_for("customer_register"))

        connection = get_db()

        existing_customer = connection.execute("""
            SELECT id FROM customers
            WHERE email = ?
        """, (email,)).fetchone()

        if existing_customer:

            connection.close()

            flash("An account with this email already exists.")

            return redirect(url_for("customer_register"))

        hashed_password = generate_password_hash(password)

        cursor = connection.execute("""
            INSERT INTO customers (
                full_name,
                email,
                phone,
                password
            )
            VALUES (?, ?, ?, ?)
        """, (
            full_name,
            email,
            phone,
            hashed_password
        ))

        customer_id = cursor.lastrowid

        # Link matching previous guest orders to this account
        connection.execute("""
            UPDATE orders
            SET customer_id = ?
            WHERE LOWER(email) = ?
            AND phone = ?
            AND customer_id IS NULL
        """, (customer_id, email, phone))

        connection.commit()
        connection.close()

        session["customer_id"] = customer_id

        flash("Your Glowora account has been created successfully!")

        return redirect(url_for("customer_account"))

    return render_template("register.html")


# ==========================================
# CUSTOMER LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def customer_login():

    if session.get("customer_id"):
        return redirect(url_for("customer_account"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")

        if not email or not password:

            flash("Please enter your email and password.")

            return redirect(url_for("customer_login"))

        connection = get_db()

        customer = connection.execute("""
            SELECT * FROM customers
            WHERE email = ?
        """, (email,)).fetchone()

        if customer and check_password_hash(
            customer["password"], password
        ):

            # Link matching previous guest orders
            connection.execute("""
                UPDATE orders
                SET customer_id = ?
                WHERE LOWER(email) = ?
                AND phone = ?
                AND customer_id IS NULL
            """, (
                customer["id"],
                customer["email"],
                customer["phone"]
            ))

            connection.commit()
            connection.close()

            session["customer_id"] = customer["id"]

            flash("Welcome back to Glowora!")

            return redirect(url_for("customer_account"))

        connection.close()

        flash("Invalid email or password.")

    return render_template("login.html")


# ==========================================
# CUSTOMER ACCOUNT
# ==========================================

@app.route("/account")
@customer_required
def customer_account():

    connection = get_db()

    customer = connection.execute("""
        SELECT id, full_name, email, phone, created_at
        FROM customers
        WHERE id = ?
    """, (session["customer_id"],)).fetchone()

    connection.close()

    if customer is None:

        session.pop("customer_id", None)

        flash("Please login again.")

        return redirect(url_for("customer_login"))

    return render_template(
        "account.html",
        customer=customer
    )


# ==========================================
# CUSTOMER ORDER HISTORY
# ==========================================

@app.route("/my-orders")
@customer_required
def my_orders():

    connection = get_db()

    customer_orders = connection.execute("""
        SELECT *
        FROM orders
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (session["customer_id"],)).fetchall()

    orders = []

    for order in customer_orders:

        items = connection.execute("""
            SELECT *
            FROM order_items
            WHERE order_id = ?
        """, (order["id"],)).fetchall()

        orders.append({
            "order": order,
            "items": items
        })

    connection.close()

    return render_template(
        "my_orders.html",
        orders=orders,
        searched=True,
        email="",
        phone=""
    )


# ==========================================
# CUSTOMER LOGOUT
# ==========================================

@app.route("/logout")
def customer_logout():

    session.pop("customer_id", None)

    flash("You have been logged out.")

    return redirect(url_for("home"))


# ==========================================
# ADMIN LOGIN
# ==========================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_logged_in"):

        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        flash("Invalid username or password!")

    return render_template("admin_login.html")


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    connection = get_db()

    total_products = connection.execute("""
        SELECT COUNT(*) FROM products
    """).fetchone()[0]

    total_orders = connection.execute("""
        SELECT COUNT(*) FROM orders
    """).fetchone()[0]

    total_sales = connection.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM orders
    """).fetchone()[0]

    recent_orders = connection.execute("""
        SELECT * FROM orders
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    products = connection.execute("""
        SELECT * FROM products
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        total_sales=total_sales,
        recent_orders=recent_orders,
        products=products
    )


# ==========================================
# ADD NEW PRODUCT WITH IMAGE UPLOAD
# ==========================================

@app.route("/admin/add-product", methods=["GET", "POST"])
@admin_required
def admin_add_product():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price_text = request.form.get("price", "").strip()

        uploaded_file = request.files.get("image_file")

        if not all([name, category, description, price_text]):

            flash("Please fill in all product details.")

            return redirect(url_for("admin_add_product"))

        try:
            price = float(price_text)

        except ValueError:

            flash("Please enter a valid product price.")

            return redirect(url_for("admin_add_product"))

        if price <= 0:

            flash("Product price must be greater than zero.")

            return redirect(url_for("admin_add_product"))

        if not uploaded_file or uploaded_file.filename == "":

            flash("Please select a product image.")

            return redirect(url_for("admin_add_product"))

        original_filename = secure_filename(uploaded_file.filename)

        extension = Path(original_filename).suffix.lower().lstrip(".")

        if extension not in ALLOWED_EXTENSIONS:

            flash("Only JPG, JPEG, PNG and WEBP images are allowed.")

            return redirect(url_for("admin_add_product"))

        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid4().hex}.{extension}"

        image_path = f"/static/uploads/{unique_filename}"

        uploaded_file.save(UPLOAD_FOLDER / unique_filename)

        connection = get_db()

        connection.execute("""
            INSERT INTO products (
                name,
                category,
                price,
                description,
                image
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            category,
            price,
            description,
            image_path
        ))

        connection.commit()
        connection.close()

        flash("Product added successfully!")

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_add_product.html")


# ==========================================
# EDIT PRODUCT
# ==========================================

@app.route("/admin/edit-product/<int:product_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_product(product_id):

    connection = get_db()

    product = connection.execute("""
        SELECT * FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if product is None:

        connection.close()

        abort(404)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price_text = request.form.get("price", "").strip()

        uploaded_file = request.files.get("image_file")

        image = product["image"]

        if not all([name, category, description, price_text]):

            connection.close()

            flash("Please fill in all product details.")

            return redirect(url_for(
                "admin_edit_product",
                product_id=product_id
            ))

        try:
            price = float(price_text)

        except ValueError:

            connection.close()

            flash("Please enter a valid price.")

            return redirect(url_for(
                "admin_edit_product",
                product_id=product_id
            ))

        if price <= 0:

            connection.close()

            flash("Price must be greater than zero.")

            return redirect(url_for(
                "admin_edit_product",
                product_id=product_id
            ))

        if uploaded_file and uploaded_file.filename:

            original_filename = secure_filename(uploaded_file.filename)

            extension = Path(original_filename).suffix.lower().lstrip(".")

            if extension not in ALLOWED_EXTENSIONS:

                connection.close()

                flash("Only JPG, JPEG, PNG and WEBP images are allowed.")

                return redirect(url_for(
                    "admin_edit_product",
                    product_id=product_id
                ))

            UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

            unique_filename = f"{uuid4().hex}.{extension}"

            image = f"/static/uploads/{unique_filename}"

            uploaded_file.save(UPLOAD_FOLDER / unique_filename)

        connection.execute("""
            UPDATE products
            SET name = ?,
                category = ?,
                price = ?,
                description = ?,
                image = ?
            WHERE id = ?
        """, (
            name,
            category,
            price,
            description,
            image,
            product_id
        ))

        connection.commit()
        connection.close()

        flash("Product updated successfully!")

        return redirect(url_for("admin_dashboard"))

    connection.close()

    return render_template(
        "admin_edit_product.html",
        product=product
    )


# ==========================================
# DELETE PRODUCT
# ==========================================

@app.route(
    "/admin/delete-product/<int:product_id>",
    methods=["POST"]
)
@admin_required
def admin_delete_product(product_id):

    connection = get_db()

    product = connection.execute("""
        SELECT id FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if product is None:

        connection.close()

        flash("Product not found.")

        return redirect(url_for("admin_dashboard"))

    connection.execute("""
        DELETE FROM products
        WHERE id = ?
    """, (product_id,))

    connection.commit()
    connection.close()

    cart = session.get("cart", {})

    cart.pop(str(product_id), None)

    session["cart"] = cart

    flash("Product deleted successfully!")

    return redirect(url_for("admin_dashboard"))


# ==========================================
# ADMIN ORDER MANAGEMENT
# ==========================================

@app.route("/admin/orders")
@admin_required
def admin_orders():

    connection = get_db()

    all_orders = connection.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """).fetchall()

    orders = []

    for order in all_orders:

        items = connection.execute("""
            SELECT *
            FROM order_items
            WHERE order_id = ?
        """, (order["id"],)).fetchall()

        orders.append({
            "order": order,
            "products": items
        })

    connection.close()

    return render_template(
        "admin_orders.html",
        orders=orders
    )


# ==========================================
# UPDATE ORDER STATUS
# ==========================================

@app.route("/admin/orders/update/<int:order_id>", methods=["POST"])
@admin_required
def admin_update_order_status(order_id):

    new_status = request.form.get("status", "").strip()

    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Shipped",
        "Delivered",
        "Cancelled"
    ]

    if new_status not in allowed_statuses:

        flash("Invalid order status.")

        return redirect(url_for("admin_orders"))

    connection = get_db()

    order = connection.execute("""
        SELECT id FROM orders
        WHERE id = ?
    """, (order_id,)).fetchone()

    if order is None:

        connection.close()

        flash("Order not found.")

        return redirect(url_for("admin_orders"))

    connection.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (new_status, order_id))

    connection.commit()
    connection.close()

    flash("Order status updated successfully!")

    return redirect(url_for("admin_orders"))


# ==========================================
# ADMIN LOGOUT
# ==========================================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("admin_login"))


# ==========================================
# RUN FLASK APPLICATION
# ==========================================

# Runs on import too, so tables are created on PythonAnywhere/Render
initialize_database()

if __name__ == "__main__":

    app.run(debug=False)
