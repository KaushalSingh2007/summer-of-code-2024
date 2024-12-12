from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)

# Replace with your PostgreSQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:kaushal@localhost:5432/bank'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with app
db = SQLAlchemy(app)

# Models
class InventoryItem(db.Model):
    __tablename__ = 'inventory_item'  # Specify table name
    Item_SKU = db.Column(db.String(20), primary_key=True)
    Item_Name = db.Column(db.String(50), nullable=False)
    Item_Description = db.Column(db.String(200))
    Item_qty = db.Column(db.Integer, nullable=False)

class Customer(db.Model):
    __tablename__ = 'customer'  # Specify table name
    c_ID = db.Column(db.Integer, primary_key=True)
    c_name = db.Column(db.String(50), nullable=False)
    c_email = db.Column(db.String(100), nullable=False)
    c_contact = db.Column(db.String(15), nullable=False)

class Staff(db.Model):
    __tablename__ = 'staff'  # Specify table name
    s_ID = db.Column(db.Integer, primary_key=True)
    s_name = db.Column(db.String(50), nullable=False)
    s_email = db.Column(db.String(100), nullable=False)
    s_contact = db.Column(db.String(15), nullable=False)

class Transaction(db.Model):
    __tablename__ = 'transaction'  # Specify table name
    t_id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey('customer.c_ID'), nullable=False)
    t_date = db.Column(db.Date, nullable=False)
    t_amount = db.Column(db.Float, nullable=False)
    t_category = db.Column(db.String(50), nullable=False)

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/inventory')
def inventory():
    items = InventoryItem.query.all()
    return render_template('inventory.html', items=items)

@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if request.method == 'POST':
        item = InventoryItem(
            Item_SKU=request.form['Item_SKU'],
            Item_Name=request.form['Item_Name'],
            Item_Description=request.form['Item_Description'],
            Item_qty=request.form['Item_qty']
        )
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('inventory'))
    return render_template('add_inventory.html')

@app.route('/customers')
def customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/staff')
def staff():
    staff_list = Staff.query.all()
    return render_template('staff.html', staff_list=staff_list)

@app.route('/transactions')
def transactions():
    transactions = Transaction.query.all()
    return render_template('transactions.html', transactions=transactions)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        transaction = Transaction(
            c_id=request.form['c_id'],
            t_date=datetime.strptime(request.form['t_date'], '%Y-%m-%d'),
            t_amount=request.form['t_amount'],
            t_category=request.form['t_category']
        )
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('transactions'))
    return render_template('add_transaction.html')

# Initialize the database and create tables when the app runs
def init_db():
    with app.app_context():  # Ensure app context is active
        db.create_all()  # Create tables in PostgreSQL

# Main block to run the app and initialize the database
if __name__ == '__main__':
    init_db()  # Initialize the database tables before running the app
    app.run(debug=True)


