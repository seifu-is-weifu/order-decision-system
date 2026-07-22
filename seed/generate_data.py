import boto3
import random
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

customers_table = dynamodb.Table('Customers')
inventory_table = dynamodb.Table('Inventory')
orders_table = dynamodb.Table('Orders')

NUM_CUSTOMERS = 10000
NUM_ORDERS = 150000

PRODUCTS = [
    {'sku': 'IPHONE16-128', 'name': 'iPhone 16 128GB',
        'category': 'Electronics', 'price': 999},
    {'sku': 'AIRPODS-PRO2', 'name': 'AirPods Pro 2',
        'category': 'Electronics', 'price': 249},
    {'sku': 'PS5-SLIM', 'name': 'PlayStation 5 Slim',
        'category': 'Gaming', 'price': 549},
    {'sku': 'MACBOOK-AIR', 'name': 'MacBook Air',
        'category': 'Electronics', 'price': 1299},
    {'sku': 'GAMING-CHAIR', 'name': 'Gaming Chair',
        'category': 'Furniture', 'price': 399},
    {'sku': 'SSD-1TB', 'name': 'SSD 1TB', 'category': 'Electronics', 'price': 129},
]


def generate_customers():
    customers = []
    with customers_table.batch_writer() as batch:
        for i in range(NUM_CUSTOMERS):
            customer_id = f'CUST{i:06d}'
            tenure_days = random.randint(1, 3650)
            join_date = datetime.utcnow() - timedelta(days=tenure_days)

            if tenure_days > 1000:
                ltv = random.randint(1000, 20000)
                total_orders = random.randint(20, 200)
            elif tenure_days > 180:
                ltv = random.randint(200, 5000)
                total_orders = random.randint(5, 50)
            else:
                ltv = random.randint(0, 500)
                total_orders = random.randint(0, 10)

            customer = {
                'customerId': customer_id,
                'joinDate': join_date.isoformat(),
                'customerTenureDays': tenure_days,
                'lifetimeValue': Decimal(str(ltv)),
                'totalOrders': total_orders,
            }

            batch.put_item(Item=customer)
            customers.append(customer)

    return customers


def generate_inventory():
    with inventory_table.batch_writer() as batch:
        for product in PRODUCTS:
            item = {
                'sku': product['sku'],
                'productName': product['name'],
                'category': product['category'],
                'price': Decimal(str(product['price'])),
                'stock': random.randint(0, 100),
            }
            batch.put_item(Item=item)


def generate_orders(customers):
    with orders_table.batch_writer() as batch:
        for i in range(NUM_ORDERS):
            customer = random.choice(customers)
            product = random.choice(PRODUCTS)

            order_time = datetime.utcnow() - timedelta(minutes=random.randint(0, 60 * 24 * 90))

            basket_value = product['price'] * random.randint(1, 3)

            fraud_score = random.randint(1, 40)
            payment_attempts = 1

            if random.random() < 0.025:
                fraud_score = random.randint(85, 99)
                payment_attempts = random.randint(3, 6)
                basket_value *= random.randint(2, 5)

            order = {
                'orderId': f'ORD{i:08d}',
                'customerId': customer['customerId'],
                'sku': product['sku'],
                'orderTimestamp': order_time.isoformat(),
                'basketValue': Decimal(str(round(basket_value, 2))),
                'paymentMethod': random.choice(['VISA', 'MASTERCARD', 'PAYPAL', 'APPLE_PAY']),
                'paymentAttempts': payment_attempts,
                'fraudScore': fraud_score,
                'decision': 'PENDING',
            }

            batch.put_item(Item=order)

            if i % 10000 == 0 and i > 0:
                print(f'Generated {i} orders...')


if __name__ == '__main__':
    print('Generating customers...')
    customers = generate_customers()

    print('Generating inventory...')
    generate_inventory()

    print('Generating orders...')
    generate_orders(customers)

    print('Done!')
