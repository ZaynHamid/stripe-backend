# Stripe Backend API

A simple Flask backend for user authentication and Stripe payments/subscriptions, using MySQL for user storage.

## Features

- User registration and login with hashed passwords
- JWT-based authentication
- Stripe customer creation
- Stripe Checkout for one-time and subscription payments
- Retrieve all customer charges
- Usage-based charging
- All secrets and credentials are loaded from environment variables

## Requirements

- Python 3.8+
- MySQL database
- Stripe account

## Setup

1. **Clone the repository**

   ```sh
   git clone <your-repo-url>
   cd stripe-backend
   ```

2. **Install dependencies**

   ```sh
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the project root with the following variables:

   ```
   FLASK_SECRET_KEY=your_flask_secret_key
   STRIPE_API_KEY=your_stripe_secret_key
   DB_HOST=your_mysql_host
   DB_USER=your_mysql_user
   DB_PASSWORD=your_mysql_password
   DB_NAME=your_mysql_db_name
   ```

4. **Set up your MySQL database**

   Make sure your database has a `user` table with at least these columns:
   - `name` (VARCHAR)
   - `email` (VARCHAR, unique)
   - `password` (BLOB or VARCHAR)
   - `customerId` (VARCHAR)

5. **Run the server**

   ```sh
   python app.py
   ```

   The server will start on `http://127.0.0.1:5000/`.

## API Endpoints

### `POST /submit_creds`

Register a new user.

**Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "yourpassword"
}
```

### `POST /login`

Login and receive a JWT.

**Body:**
```json
{
  "email": "john@example.com",
  "password": "yourpassword"
}
```

### `POST /create-checkout-session`

Create a Stripe Checkout session.

**Headers:**  
`Authorization: Bearer <JWT>`

**Body:**
```json
{
  "price_id": "price_xxx",
  "is_subscription": true,
  "customer_id": "cus_xxx"
}
```

### `POST /get-all-customer-charges`

Get all Stripe charges for a customer.

**Headers:**  
`Authorization: Bearer <JWT>`

**Body:**
```json
{
  "customer_id": "cus_xxx"
}
```

### `POST /charge-user-on-usage`

Charge a customer for usage.

**Headers:**  
`Authorization: Bearer <JWT>`

**Body:**
```json
{
  "customer_id": "cus_xxx",
  "units": 5,
  "price_id": "price_xxx"
}
```

## Notes

- CORS is **not** enabled by default. If you need CORS, configure it at your proxy or web server.
- All secrets are loaded from environment variables for security.
- Do **not** commit your `.env` file to version control.

---

**License:** MIT (add your license if needed)