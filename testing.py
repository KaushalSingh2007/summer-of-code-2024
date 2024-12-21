import pytest
from app import app, db, User, Product, Transaction, bcrypt
from flask import session

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

@pytest.fixture
def create_data():
    with app.app_context():
        # Create test users
        customer = User(username="test_customer", password=bcrypt.generate_password_hash("password").decode('utf-8'), role="customer")
        admin = User(username="test_admin", password=bcrypt.generate_password_hash("password").decode('utf-8'), role="admin")
        db.session.add(customer)
        db.session.add(admin)
        db.session.commit()

        # Create test products
        product = Product(name="Test Product", price=10.99, stock=100)
        db.session.add(product)
        db.session.commit()

# Tests

def test_register(client):
    response = client.post('/auth/register', json={
        "username": "new_user",
        "password": "password",
        "role": "customer"
    })
    assert response.status_code == 201
    assert response.get_json()["message"] == "User registered successfully."

def test_login_customer(client, create_data):
    response = client.post('/auth/login', json={
        "username": "test_customer",
        "password": "password"
    })
    assert response.status_code == 200
    assert response.get_json()["role"] == "customer"
    assert response.get_json()["redirect_url"] == "/customer/dashboard"

def test_login_admin(client, create_data):
    response = client.post('/auth/login', json={
        "username": "test_admin",
        "password": "password"
    })
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"
    assert response.get_json()["redirect_url"] == "/admin/dashboard"

def test_customer_dashboard(client, create_data):
    # Log in as customer
    client.post('/auth/login', json={
        "username": "test_customer",
        "password": "password"
    })
    response = client.get('/customer/dashboard')
    assert response.status_code == 200
    assert response.get_json()["message"] == "Welcome to the customer dashboard!"

def test_admin_dashboard(client, create_data):
    # Log in as admin
    client.post('/auth/login', json={
        "username": "test_admin",
        "password": "password"
    })
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert response.get_json()["message"] == "Welcome to the admin dashboard!"

def test_protected_routes_without_login(client):
    response = client.get('/customer/dashboard')
    assert response.status_code == 401
    assert response.get_json()["message"] == "You must be logged in to access this resource."

    response = client.get('/admin/dashboard')
    assert response.status_code == 401
    assert response.get_json()["message"] == "You must be logged in to access this resource."

def test_role_protection(client, create_data):
    # Log in as customer
    client.post('/auth/login', json={
        "username": "test_customer",
        "password": "password"
    })

    # Try to access admin dashboard
    response = client.get('/admin/dashboard')
    assert response.status_code == 403
    assert response.get_json()["message"] == "Access denied for this role."

def test_customer_product_view(client, create_data):
    # Log in as customer
    client.post('/auth/login', json={
        "username": "test_customer",
        "password": "password"
    })
    response = client.get('/customer/products')
    assert response.status_code == 200
    assert len(response.get_json()) > 0  # Ensure products are returned

def test_admin_product_crud(client, create_data):
    # Log in as admin
    client.post('/auth/login', json={
        "username": "test_admin",
        "password": "password"
    })

    # Add a new product
    response = client.post('/admin/products', json={
        "name": "New Product",
        "price": 15.99,
        "stock": 50
    })
    assert response.status_code == 201
    assert response.get_json()["message"] == "Product created successfully."

    # View all products
    response = client.get('/admin/products')
    assert response.status_code == 200
    assert len(response.get_json()) > 1  # Ensure new product is added
