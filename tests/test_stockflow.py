import pytest
from app import app, db
from models import Product, Inventory, Company, Warehouse, Supplier, Sale
from decimal import Decimal
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_create_product_happy_path(client):
    with app.app_context():
        c = Company(name="Test Co")
        db.session.add(c)
        db.session.commit()
        w = Warehouse(company_id=c.id, name="Main")
        db.session.add(w)
        db.session.commit()
        w_id = w.id

    payload = {
        "name": "Widget A",
        "sku": "WID-001",
        "price": 19.99,
        "warehouse_id": w_id,
        "initial_quantity": 100
    }
    response = client.post('/api/products', json=payload)
    assert response.status_code == 201
    assert response.get_json()['message'] == "Product created"

def test_create_product_duplicate_sku(client):
    with app.app_context():
        c = Company(name="Test Co")
        db.session.add(c)
        db.session.commit()
        w = Warehouse(company_id=c.id, name="Main")
        db.session.add(w)
        db.session.commit()
        w_id = w.id

    payload = {
        "name": "Widget A",
        "sku": "WID-001",
        "price": 19.99,
        "warehouse_id": w_id,
        "initial_quantity": 100
    }
    client.post('/api/products', json=payload)
    response = client.post('/api/products', json=payload)
    assert response.status_code == 409
    assert "already exists" in response.get_json()['error']

def test_low_stock_calculation(client):
    with app.app_context():
        c = Company(name="Acme Corp")
        db.session.add(c)
        db.session.commit()
        
        w = Warehouse(company_id=c.id, name="East")
        db.session.add(w)
        db.session.commit()
        
        s = Supplier(name="Suppy", contact_email="s@s.com")
        db.session.add(s)
        db.session.commit()

        p = Product(name="Low Stock Item", sku="LS-001", price=10.0, supplier_id=s.id, low_stock_threshold=20)
        db.session.add(p)
        db.session.commit()
        
        inv = Inventory(product_id=p.id, warehouse_id=w.id, quantity=5)
        db.session.add(inv)
        db.session.commit()

        sale = Sale(product_id=p.id, warehouse_id=w.id, quantity_sold=60, sold_at=datetime.utcnow() - timedelta(days=5))
        db.session.add(sale)
        db.session.commit()

        company_id = c.id

    response = client.get(f'/api/companies/{company_id}/alerts/low-stock')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['alerts']) == 1
    alert = data['alerts'][0]
    assert alert['sku'] == "LS-001"
    assert alert['current_stock'] == 5
    assert alert['days_until_stockout'] == 2.5
    assert alert['supplier']['name'] == "Suppy"
