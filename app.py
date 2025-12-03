import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Create transactions table if it doesn't exist
db.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        shares INTEGER NOT NULL,
        price NUMERIC NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
""")
db.execute("CREATE INDEX IF NOT EXISTS user_id_on_transactions ON transactions (user_id);")
db.execute("CREATE INDEX IF NOT EXISTS symbol_on_transactions ON transactions (symbol);")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    # Get user's cash
    current_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    # Get user's stock holdings
    # Group by symbol and sum shares
    user_stocks = db.execute(
        "SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0",
        user_id,
    )

    portfolio = []
    total_value = current_cash

    for stock_item in user_stocks:
        symbol = stock_item["symbol"]
        total_shares = stock_item["total_shares"]
        quote_data = lookup(symbol)
        if quote_data:
            price = quote_data["price"]
            stock_value = total_shares * price
            total_value += stock_value
            portfolio.append(
                {
                    "symbol": symbol,
                    "name": quote_data["name"],
                    "shares": total_shares,
                    "price": price,
                    "total_value": stock_value,
                }
            )

    return render_template("index.html", stocks=portfolio, user_cash=current_cash, grand_total=total_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        num_shares = request.form.get("shares")

        # Validate symbol
        if not symbol:
            return apology("must provide symbol")
        stock_data = lookup(symbol)
        if not stock_data:
            return apology("invalid symbol")

        # Validate shares
        if not num_shares or not num_shares.isdigit() or int(num_shares) <= 0:
            return apology("must provide a positive integer for shares")
        num_shares = int(num_shares)

        share_price = stock_data["price"]
        cost = num_shares * share_price

        user_id = session["user_id"]
        user_rows = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        user_balance = user_rows[0]["cash"]

        if user_balance < cost:
            return apology("can't afford")

        # Update user's cash
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", cost, user_id)

        # Record transaction
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            user_id,
            stock_data["symbol"],
            num_shares,
            share_price,
        )

        flash(f"Bought {num_shares} shares of {stock_data['symbol']} for {usd(cost)}!")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transaction_history = db.execute(
        "SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC",
        user_id,
    )
    return render_template("history.html", transactions=transaction_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        user_data = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(user_data) != 1 or not check_password_hash(
            user_data[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user_data[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol")

        quoted_data = lookup(symbol)
        if not quoted_data:
            return apology("invalid symbol")

        return render_template("quoted.html", stock=quoted_data)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username")
        elif not password:
            return apology("must provide password")
        elif not confirmation:
            return apology("must confirm password")
        elif password != confirmation:
            return apology("passwords do not match")

        # Hash password
        password_hash = generate_password_hash(password)

        # Insert new user into database
        try:
            new_user_id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, password_hash)
            session["user_id"] = new_user_id
            return redirect("/")
        except ValueError:
            return apology("username already exists")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares_amount = request.form.get("shares")

        # Validate symbol
        if not symbol:
            return apology("must select a symbol")

        # Validate shares
        if not shares_amount or not shares_amount.isdigit() or int(shares_amount) <= 0:
            return apology("must provide a positive integer for shares")
        shares_amount = int(shares_amount)

        # Check user's current holdings for the symbol
        user_holdings = db.execute(
            "SELECT SUM(shares) as total_shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol",
            user_id,
            symbol,
        )

        if not user_holdings or user_holdings[0]["total_shares"] < shares_amount:
            return apology("you do not own that many shares of this stock")

        stock_info = lookup(symbol)
        if not stock_info:
            return apology("invalid symbol (stock no longer exists?)")

        current_price = stock_info["price"]
        sale_price = shares_amount * current_price

        # Update user's cash
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", sale_price, user_id)

        # Record transaction (negative shares for selling)
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            user_id,
            symbol,
            -shares_amount,
            current_price,
        )

        flash(f"Sold {shares_amount} shares of {symbol} for {usd(sale_price)}!")
        return redirect("/")

    else:
        # Get symbols of stocks user owns to populate the dropdown
        owned_stocks = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0",
            user_id,
        )
        return render_template("sell.html", holdings=owned_stocks)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user's password"""
    if request.method == "POST":
        old_pass = request.form.get("current_password")
        new_pass = request.form.get("new_password")
        confirm_pass = request.form.get("confirmation")

        # Validate input
        if not old_pass:
            return apology("must provide current password")
        if not new_pass:
            return apology("must provide new password")
        if not confirm_pass:
            return apology("must confirm new password")
        if new_pass != confirm_pass:
            return apology("new password and confirmation do not match")

        user_id = session["user_id"]
        user_row = db.execute("SELECT hash FROM users WHERE id = ?", user_id)
        db_hash = user_row[0]["hash"]

        # Check if current password is correct
        if not check_password_hash(db_hash, old_pass):
            return apology("invalid current password")

        # Update password
        new_pass_hash = generate_password_hash(new_pass)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_pass_hash, user_id)

        flash("Password changed successfully!")
        return redirect("/")

    else:
        return render_template("change_password.html")
