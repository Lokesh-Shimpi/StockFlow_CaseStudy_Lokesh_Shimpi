from flask import Flask, request, jsonify
from models import db, Product, Inventory, Company, Warehouse, Supplier, Sale
from decimal import Decimal, InvalidOperation
from sqlalchemy import func
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stockflow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.json
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_keys = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_keys)}"}), 400

    try:
        try:
            price = Decimal(str(data['price']))
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({"error": "Invalid price format"}), 400

        new_product = Product(
            name=data['name'],
            sku=data['sku'],
            price=price
        )
        
        db.session.add(new_product)
        db.session.flush()

        new_inventory = Inventory(
            product_id=new_product.id,
            warehouse_id=data['warehouse_id'],
            quantity=data['initial_quantity']
        )
        
        db.session.add(new_inventory)
        db.session.commit()

        return jsonify({
            "message": "Product created",
            "product_id": new_product.id
        }), 201

    except Exception as e:
        db.session.rollback()
        if "UNIQUE constraint failed: products.sku" in str(e):
             return jsonify({"error": "Product with this SKU already exists"}), 409
        return jsonify({"error": str(e)}), 500

@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Company not found"}), 404

    warehouse_id = request.args.get('warehouse_id', type=int)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    query = db.session.query(
        Product, 
        Inventory, 
        Warehouse, 
        Supplier
    ).join(Inventory, Product.id == Inventory.product_id) \
     .join(Warehouse, Inventory.warehouse_id == Warehouse.id) \
     .outerjoin(Supplier, Product.supplier_id == Supplier.id) \
     .filter(Warehouse.company_id == company_id)

    if warehouse_id:
        query = query.filter(Warehouse.id == warehouse_id)

    sales_subquery = db.session.query(
        Sale.product_id,
        Sale.warehouse_id,
        func.sum(Sale.quantity_sold).label('total_sold')
    ).filter(Sale.sold_at >= thirty_days_ago) \
     .group_by(Sale.product_id, Sale.warehouse_id).subquery()

    query = query.join(sales_subquery, (Product.id == sales_subquery.c.product_id) & (Warehouse.id == sales_subquery.c.warehouse_id))
    query = query.filter(Inventory.quantity <= Product.low_stock_threshold)

    total = query.count()
    results = query.offset((page - 1) * limit).limit(limit).all()

    alerts = []
    for product, inventory, warehouse, supplier in results:
        total_sold_last_30 = db.session.query(func.sum(Sale.quantity_sold)) \
            .filter(Sale.product_id == product.id) \
            .filter(Sale.warehouse_id == warehouse.id) \
            .filter(Sale.sold_at >= thirty_days_ago).scalar() or 0
        
        avg_daily_sales = total_sold_last_30 / 30.0
        
        if avg_daily_sales > 0:
            days_until_stockout = round(inventory.quantity / avg_daily_sales, 1)
        else:
            days_until_stockout = 999.0

        alerts.append({
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "current_stock": inventory.quantity,
            "threshold": product.low_stock_threshold,
            "days_until_stockout": days_until_stockout,
            "supplier": {
                "id": supplier.id if supplier else None,
                "name": supplier.name if supplier else "Unknown",
                "contact_email": supplier.contact_email if supplier else "N/A"
            }
        })

    return jsonify({
        "alerts": alerts,
        "total_alerts": total
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
