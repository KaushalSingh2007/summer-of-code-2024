from flask import Flask, request, jsonify, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_restx import Api, Resource, fields, Namespace
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from flask_migrate import Migrate
import pyotp
import logging
from datetime import datetime

# Initialize Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'singhkaushaltomar@gmail.com'
app.config['MAIL_PASSWORD'] = 'Kjee@2024AIR1'

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)
mail = Mail(app)
api = Api(app, version='1.0', title='API', description='CRUD operations and Authentication')

# Configure login manager
login_manager.login_view = 'login'
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
logging.basicConfig(filename='auth.log', level=logging.INFO)

# Namespaces
auth_ns = Namespace('auth', description='Authentication operations')
transaction_ns = Namespace('transactions', description='Transaction operations')
staff_ns = Namespace('staff', description='Staff operations')
customer_ns = Namespace('customers', description='Customer operations')

api.add_namespace(auth_ns)
api.add_namespace(transaction_ns)
api.add_namespace(staff_ns)
api.add_namespace(customer_ns)

# Database Models
class Staff(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(128), nullable=True)
    totp_secret = db.Column(db.String(16), default=pyotp.random_base32)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    s_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    product_amount_list = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)

    customer = db.relationship('Customer', backref=db.backref('transactions', lazy=True))
    staff = db.relationship('Staff', backref=db.backref('transactions', lazy=True))

# API Models
login_model = api.model('Login', {
    'email': fields.String(required=True),
    'password': fields.String(required=True),
})

register_model = api.model('Register', {
    'username': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String(required=True),
})

transaction_model = api.model('Transaction', {
    'id': fields.Integer(),
    'c_id': fields.Integer(required=True),
    's_id': fields.Integer(required=True),
    'product_amount_list': fields.String(required=True),
    'date': fields.String(required=True),
    'time': fields.String(required=True),
})

customer_model = api.model('Customer', {
    'id': fields.Integer(),
    'name': fields.String(required=True),
    'email': fields.String(required=True),
})

staff_model = api.model('Staff', {
    'id': fields.Integer(),
    'username': fields.String(),
    'email': fields.String(),
    'is_admin': fields.Boolean(),
    'is_approved': fields.Boolean(),
})

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return Staff.query.get(int(user_id))

# Helper Functions
def hash_password(password):
    return bcrypt.generate_password_hash(password).decode('utf-8')

def verify_password(hashed_password, input_password):
    return bcrypt.check_password_hash(hashed_password, input_password)

def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)

# Authentication Routes
@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    def post(self):
        data = request.json
        if Staff.query.filter_by(email=data['email']).first():
            return {'message': 'Email already registered.'}, 400
        if Staff.query.filter_by(username=data['username']).first():
            return {'message': 'Username already exists.'}, 400
        
        hashed_password = hash_password(data['password'])
        token = serializer.dumps(data['email'], salt='email-verification')
        new_staff = Staff(username=data['username'], email=data['email'], password=hashed_password, verification_token=token)
        db.session.add(new_staff)
        db.session.commit()

        verification_link = url_for('auth_verify_email', token=token, _external=True)
        send_email('Verify Your Email', data['email'], f'Click to verify: {verification_link}')
        return {'message': 'Registered successfully. Verify your email.'}, 201

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        data = request.json
        user = Staff.query.filter_by(email=data['email']).first()
        if user and verify_password(user.password, data['password']):
            login_user(user)
            return {'message': 'Login successful.'}, 200
        return {'message': 'Invalid credentials.'}, 401

@auth_ns.route('/logout')
class Logout(Resource):
    @login_required
    def post(self):
        logout_user()
        return {'message': 'Logout successful.'}, 200

@auth_ns.route('/verify_email/<token>')
class VerifyEmail(Resource):
    def get(self, token):
        try:
            email = serializer.loads(token, salt='email-verification', max_age=3600)
            user = Staff.query.filter_by(email=email).first()
            if user:
                user.is_email_verified = True
                db.session.commit()
                return {'message': 'Email verified successfully.'}, 200
            return {'message': 'Invalid or expired link.'}, 400
        except Exception as e:
            return {'message': str(e)}, 400

# Transaction CRUD
@transaction_ns.route('/')
class Transactions(Resource):
    @transaction_ns.marshal_with(transaction_model)
    def get(self):
        return Transaction.query.all()

    @transaction_ns.expect(transaction_model)
    def post(self):
        data = request.json
        new_transaction = Transaction(**data)
        db.session.add(new_transaction)
        db.session.commit()
        return {'message': 'Transaction created successfully.'}, 201

@transaction_ns.route('/<int:id>')
class TransactionById(Resource):
    @transaction_ns.marshal_with(transaction_model)
    def get(self, id):
        return Transaction.query.get_or_404(id)

    def delete(self, id):
        transaction = Transaction.query.get_or_404(id)
        db.session.delete(transaction)
        db.session.commit()
        return {'message': 'Transaction deleted successfully.'}, 200

    @transaction_ns.expect(transaction_model)
    def put(self, id):
        data = request.json
        transaction = Transaction.query.get_or_404(id)
        transaction.product_amount_list = data['product_amount_list']
        transaction.date = data['date']
        transaction.time = data['time']
        db.session.commit()
        return {'message': 'Transaction updated successfully.'}, 200

# Staff CRUD
@staff_ns.route('/')
class StaffList(Resource):
    @staff_ns.marshal_with(staff_model)
    def get(self):
        return Staff.query.all()

    @staff_ns.expect(staff_model)
    def post(self):
        data = request.json
        if Staff.query.filter_by(email=data['email']).first():
            return {'message': 'Email already exists.'}, 400
        hashed_password = hash_password(data['password'])
        new_staff = Staff(username=data['username'], email=data['email'], password=hashed_password)
        db.session.add(new_staff)
        db.session.commit()
        return {'message': 'Staff created successfully.'}, 201

@staff_ns.route('/<int:id>')
class StaffById(Resource):
    @staff_ns.marshal_with(staff_model)
    def get(self, id):
        return Staff.query.get_or_404(id)

    def delete(self, id):
        staff = Staff.query.get_or_404(id)
        db.session.delete(staff)
        db.session.commit()
        return {'message': 'Staff deleted successfully.'}, 200

    @staff_ns.expect(staff_model)
    def put(self, id):
        data = request.json
        staff = Staff.query.get_or_404(id)
        staff.username = data['username']
        staff.email = data['email']
        db.session.commit()
        return {'message': 'Staff updated successfully.'}, 200

# Customer CRUD
@customer_ns.route('/')
class CustomerList(Resource):
    @customer_ns.marshal_with(customer_model)
    def get(self):
        return Customer.query.all()

    @customer_ns.expect(customer_model)
    def post(self):
        data = request.json
        if Customer.query.filter_by(email=data['email']).first():
            return {'message': 'Email already exists.'}, 400
        new_customer = Customer(name=data['name'], email=data['email'])
        db.session.add(new_customer)
        db.session.commit()
        return {'message': 'Customer created successfully.'}, 201

@customer_ns.route('/<int:id>')
class CustomerById(Resource):
    @customer_ns.marshal_with(customer_model)
    def get(self, id):
        return Customer.query.get_or_404(id)

    def delete(self, id):
        customer = Customer.query.get_or_404(id)
        db.session.delete(customer)
        db.session.commit()
        return {'message': 'Customer deleted successfully.'}, 200

    @customer_ns.expect(customer_model)
    def put(self, id):
        data = request.json
        customer = Customer.query.get_or_404(id)
        customer.name = data['name']
        customer.email = data['email']
        db.session.commit()
        return {'message': 'Customer updated successfully.'}, 200

if __name__ == '__main__':
    app.run(debug=True)
