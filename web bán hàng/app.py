from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from flask import jsonify
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'shop.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('home.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db()
        cursor = conn.cursor()
        
        # Kiểm tra xem username đã tồn tại hay chưa
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Tên tài khoản đã tồn tại', 'danger')
            return redirect(url_for('register'))

        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        conn.close()
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?', (user_id, product_id))
    cart_item = cursor.fetchone()

    if cart_item:
        cursor.execute('UPDATE cart_items SET quantity = quantity + 1 WHERE id = ?', (cart_item['id'],))
    else:
        cursor.execute('INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)', (user_id, product_id, 1))

    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT products.id, products.name, products.price,products.image,cart_items.quantity 
    FROM products
    JOIN cart_items ON products.id = cart_items.product_id
    WHERE cart_items.user_id = ?
    ''', (user_id,))
    cart_items = cursor.fetchall()
    conn.close()

    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'user_id' not in session:
        flash('Please log in to modify your cart.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart_items WHERE user_id = ? AND product_id = ?', (user_id, product_id))
    conn.commit()
    conn.close()

    flash('Item removed from cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/thank_you_order')
def thank_you_order():
    return render_template('thank_you_order.html')

@app.route('/thank_you_review')
def thank_you_review():
    return render_template('thank_you_review.html')

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Chỉ có quản trị viên mới có quyền truy cập.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    cursor.execute("SELECT * FROM reviews")
    reviews = cursor.fetchall()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', orders=orders, reviews=reviews,users=users)


@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Chỉ có quản trị viên mới có quyền truy cập.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()
    flash('Đánh giá đã được xóa thành công.', 'success')
    return redirect(url_for('admin'))

@app.route('/about', methods=['GET', 'POST'])
def about():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để truy cập trang này.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'review_form' in request.form:
            product_review = request.form['product_review']
            rating = request.form['rating']

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO reviews (product_review, rating) VALUES (?, ?)", (product_review, rating))
            conn.commit()
            conn.close()

            return redirect(url_for('thank_you_review'))
    return render_template('about.html')
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Chỉ có quản trị viên mới có quyền truy cập.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash('Tài khoản đã được xóa thành công.', 'success')   
    return redirect(url_for('admin'))
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để đặt hàng.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        username = session['username']
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        phone = request.form['phone']
        gender = request.form['gender']

        conn = get_db()
        cursor = conn.cursor()

        # Get cart items
        cursor.execute('''
        SELECT ci.product_id, p.name AS product_name, ci.quantity, p.price AS price_per_unit
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id = ?
        ''', (user_id,))
        cart_items = cursor.fetchall()

        # Insert into orders_info table
        for item in cart_items:
            product_id = item['product_id']
            product_name = item['product_name']
            quantity = item['quantity']
            price_per_unit = item['price_per_unit']

            cursor.execute('''
            INSERT INTO orders_info (user_id, username, name, age, address, phone, gender, product_id, product_name, quantity, price_per_unit, order_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            ''', (user_id, username, name, age, address, phone, gender, product_id, product_name, quantity, price_per_unit))

        # Clear cart items after order
        cursor.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        flash('Đặt hàng thành công!', 'success')
        return redirect(url_for('thank_you_order'))

    return render_template('checkout.html')

@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Chỉ có quản trị viên mới có quyền truy cập.')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch orders information
    cursor.execute('''
        SELECT oi.id, oi.username, oi.name, oi.age, oi.address, oi.phone, oi.gender, oi.product_name, oi.quantity, oi.price_per_unit,
               (oi.quantity * oi.price_per_unit) AS total_price
        FROM orders_info oi
    ''')
    orders_info = cursor.fetchall()

    conn.close()

    return render_template('admin_orders.html', orders_info=orders_info)

@app.route('/admin/orders/<int:order_id>/delete', methods=['POST'])
def delete_order_admin(order_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'message': 'Chỉ có quản trị viên mới có quyền xóa đơn hàng.'}), 403

    conn = get_db()
    cursor = conn.cursor()

    # Delete order from orders_info table
    cursor.execute('DELETE FROM orders_info WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Đã xóa đơn hàng thành công.'})

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/admin/manage_products', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Chỉ có quản trị viên mới có quyền truy cập.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        file = request.files['image']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO products (name, price, description, image) VALUES (?, ?, ?, ?)',
                           (name, price, description, filename))
            conn.commit()
            conn.close()
            return redirect(url_for('admin'))

    return render_template('add_product.html')

@app.route('/order_history')
def order_history():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem lịch sử đơn hàng.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT orders_info.id, orders_info .product_name, orders_info .quantity, orders_info .price_per_unit, (orders_info .quantity * orders_info .price_per_unit) AS total_price, orders_info.order_date
        FROM orders_info 
        WHERE orders_info .user_id = ?
        ORDER BY orders_info.order_date DESC
    ''', (user_id,))
    orders = cursor.fetchall()
    conn.close()

    return render_template('order_history.html', orders=orders)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('query')
        # Xử lý tìm kiếm ở đây (ví dụ: từ cơ sở dữ liệu)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE name LIKE ?", ('%' + query + '%',))
        products = cursor.fetchall()
        conn.close()
        return render_template('home.html', products=products, query=query)

    return redirect(url_for('home'))  # Nếu là GET request hoặc không có kết quả, chuyển hướng về trang chủ
if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)
