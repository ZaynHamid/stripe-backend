import os
from flask import Flask, jsonify, request, g
import bcrypt
import mysql.connector
import jwt
from dotenv import load_dotenv
import datetime
from functools import wraps
import stripe

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")
stripe.api_key = os.getenv("STRIPE_API_KEY")
app.config['SECRET_KEY'] = app.secret_key


def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.teardown_appcontext
def teardown_db(e=None):
    close_db()


def generate_jwt(email):
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=160)
    payload = {'email': email, 'exp': expiration_time}
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")
    return token

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        try:
            if 'Authorization' in request.headers:
                token = request.headers['Authorization'].split(" ")[1]

            if not token:
                return jsonify({"message": "Token is missing!"}), 403

            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_email = data['email']
        except IndexError:
            return jsonify({"message": "Malformed Authorization header"}), 400
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"message": f"Invalid token: {str(e)}"}), 401
        except Exception as e:
            return jsonify({"message": f"Unexpected error: {str(e)}"}), 500

        return f(current_user_email, *args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return "hi"

@app.route("/submit_creds", methods=['POST', 'OPTIONS'])
def submit_creds():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.json
    name = data.get("name")
    email = data.get("email")
    pswd = data.get("password")

    salt = bcrypt.gensalt()
    hashed_pswd = bcrypt.hashpw(pswd.encode("utf-8"), salt)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"msg": "User already exists!"}), 400

    customer = stripe.Customer.create(email=email)
    cursor.execute(
        "INSERT INTO user (name, email, password, customerId) VALUES (%s, %s, %s, %s)",
        (name, email, hashed_pswd, customer.id)
    )
    db.commit()

    return jsonify({
        "msg": f"Hello {name}, Creds Successfully Received!",
        "pswd": pswd,
        "name": name,
        "email": email,
        "customerId": customer.id
    }), 201

@app.route("/login", methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.json
    email = data.get("email")
    pswd = data.get("password")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT email, password, name, customerId FROM user WHERE email=%s", (email,))
    user_ex = cursor.fetchone()

    if user_ex:
        stored_email, stored_password, name, customerId = user_ex
        if bcrypt.checkpw(pswd.encode("utf-8"), stored_password.encode("utf-8")):
            token = generate_jwt(stored_email)
            return jsonify({
                "message": "Logged in!",
                "token": token,
                "email": email,
                "user": name,
                "customerId": customerId
            })
        else:
            return jsonify({"message": "Invalid password"}), 401

    return jsonify({"msg": "User doesn't exist!"}), 404

@app.route('/create-checkout-session', methods=["OPTIONS", 'POST'])
@token_required
def create_checkout_session(user):
    data = request.json
    price_id = data.get('price_id')
    is_subscription = data.get('is_subscription')
    customer_id = data.get('customer_id')
    mode = "subscription" if is_subscription else "payment"

    if not price_id or not customer_id:
        return jsonify({'error': 'Missing Price ID or Customer ID'}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{'price': price_id, 'quantity': 1}],
            mode=mode,
            success_url='https://stripebyz.vercel.app',
            cancel_url='https://stripebyz.vercel.app/marketplace'
        )
        return jsonify({'session_url': checkout_session.url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-all-customer-charges', methods=["OPTIONS", 'POST'])
@token_required
def get_all_customer_charges(user):
    data = request.json
    customer_id = data.get('customer_id')

    all_charges = []
    has_more = True
    starting_after = None

    while has_more:
        charges = stripe.Charge.list(
            customer=customer_id,
            limit=100,
            starting_after=starting_after
        )
        all_charges.extend(charges['data'])
        has_more = charges['has_more']
        if has_more:
            starting_after = charges['data'][-1]['id']

    transactions = [
        {
            'id': charge['id'],
            'amount': charge['amount'] / 100,
            'currency': charge['currency'].upper(),
            'status': charge['status'].capitalize(),
            'created': charge['created'],
        }
        for charge in all_charges
    ]

    return jsonify({'transactions': transactions}), 200

@app.route('/charge-user-on-usage', methods=["OPTIONS", 'POST'])
@token_required
def handle_usage_based_charges(user):
    data = request.json
    customer_id = data.get('customer_id')
    units = data.get('units')
    price_id = data.get('price_id')

    if not customer_id or not units or not price_id:
        return jsonify({'error': 'Missing Customer ID, Units, or Price ID'}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{'price': price_id, 'quantity': units}],
            mode='payment',
            success_url='http://localhost:3000',
            cancel_url='http://localhost:3000/cancel.html'
        )
        return jsonify({'session_url': checkout_session.url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
