from flask import Flask, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_restx import Api, Resource, fields
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:kaushal@localhost/appdata'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
api = Api(app, title="E-commerce App", description="Role-based E-commerce API")

# Namespaces
auth_ns = api.namespace('auth', description='Authentication')
customer_ns = api.namespace('customer', description='Customer Operations')
admin_ns = api.namespace('admin', description='Admin Operations')

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'customer' or 'admin'

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# Decorator for login and role-based access
def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return {"message": "You must be logged in to access this resource."}, 401
            if role and session.get('role') != role:
                return {"message": "Access denied for this role."}, 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

# API Models
user_model = api.model('User', {
    'username': fields.String(required=True),
    'password': fields.String(required=True),
    'role': fields.String(required=True, enum=['customer', 'admin'])
})

login_model = api.model('Login', {
    'username': fields.String(required=True),
    'password': fields.String(required=True)
})

product_model = api.model('Product', {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(required=True),
    'price': fields.Float(required=True),
    'stock': fields.Integer(required=True)
})

transaction_model = api.model('Transaction', {
    'id': fields.Integer(readOnly=True),
    'user_id': fields.Integer(required=True),
    'product_id': fields.Integer(required=True),
    'quantity': fields.Integer(required=True)
})

# Authentication Endpoints
@auth_ns.route('/register')
class Register(Resource):
    @api.expect(user_model)
    def post(self):
        data = api.payload
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(username=data['username'], password=hashed_password, role=data['role'])
        db.session.add(new_user)
        db.session.commit()
        return {"message": "User registered successfully."}, 201

@auth_ns.route('/login')
class Login(Resource):
    @api.expect(login_model)
    def post(self):
        data = api.payload
        user = User.query.filter_by(username=data['username']).first()
        if user and bcrypt.check_password_hash(user.password, data['password']):
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'customer':
                return {"message": "Login successful", "role": "customer", "redirect_url": "/customer/dashboard"}, 200
            elif user.role == 'admin':
                return {"message": "Login successful", "role": "admin", "redirect_url": "/admin/dashboard"}, 200
        return {"message": "Invalid username or password"}, 401

@auth_ns.route('/logout')
class Logout(Resource):
    def get(self):
        session.clear()
        return {"message": "Logged out successfully."}, 200

# Customer Endpoints
@customer_ns.route('/dashboard')
class CustomerDashboard(Resource):
    @login_required(role='customer')
    def get(self):
        return {"message": "Welcome to the customer dashboard!"}, 200

@customer_ns.route('/products')
class CustomerProducts(Resource):
    @login_required(role='customer')
    @api.marshal_list_with(product_model)
    def get(self):
        return Product.query.all()

@customer_ns.route('/transactions')
class CustomerTransactions(Resource):
    @login_required(role='customer')
    @api.marshal_list_with(transaction_model)
    def get(self):
        user_id = session.get('user_id')
        return Transaction.query.filter_by(user_id=user_id).all()

# Admin Endpoints
@admin_ns.route('/dashboard')
class AdminDashboard(Resource):
    @login_required(role='admin')
    def get(self):
        return {"message": "Welcome to the admin dashboard!"}, 200

@admin_ns.route('/products')
class AdminProducts(Resource):
    @login_required(role='admin')
    @api.marshal_list_with(product_model)
    def get(self):
        return Product.query.all()

    @login_required(role='admin')
    @api.expect(product_model)
    def post(self):
        data = api.payload
        new_product = Product(name=data['name'], price=data['price'], stock=data['stock'])
        db.session.add(new_product)
        db.session.commit()
        return {"message": "Product created successfully."}, 201

@admin_ns.route('/transactions')
class AdminTransactions(Resource):
    @login_required(role='admin')
    @api.marshal_list_with(transaction_model)
    def get(self):
        return Transaction.query.all()

# Run the Application
if __name__ == '__main__':
    app.run(debug=True)
