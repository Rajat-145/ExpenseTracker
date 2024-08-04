from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

# Database configuration
db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME')
}

# Database connection function
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def home():
    if 'user_id' not in session:
        flash('Please login to access this page.')
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        user = cursor.fetchone()

        if user:
            flash('Username or email already exists!')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                           (username, hashed_password, email))
            conn.commit()
            flash('Registration successful!')
            return redirect(url_for('login'))

        cursor.close()
        conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password!')

        cursor.close()
        conn.close()

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

# Expense management routes
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    data = request.get_json()
    category = data['category']
    amount = data['amount']
    comments = data.get('comments', '')
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (user_id, category, amount, comments)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, category, amount, comments))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Expense added successfully'}), 201

@app.route('/view_expenses', methods=['GET'])
def view_expenses():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, category, amount, created_at, updated_at, comments
        FROM expenses WHERE user_id = %s ORDER BY created_at DESC
    ''', (user_id,))
    expenses = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(expenses)

@app.route('/edit_expense/<int:expense_id>', methods=['PUT'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    data = request.get_json()
    category = data['category']
    amount = data['amount']
    comments = data.get('comments', '')
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE expenses
        SET category = %s, amount = %s, comments = %s
        WHERE id = %s AND user_id = %s
    ''', (category, amount, comments, expense_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Expense updated successfully'})

@app.route('/delete_expense/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM expenses WHERE id = %s AND user_id = %s
    ''', (expense_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Expense deleted successfully'})

@app.route('/expense_distribution', methods=['GET'])
def expense_distribution():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, SUM(amount) as total_amount
        FROM expenses
        WHERE user_id = %s
        GROUP BY category
    ''', (user_id,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
