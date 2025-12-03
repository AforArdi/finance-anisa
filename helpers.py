import requests

from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Generates a page to display an error message."""

    def escape(s):
        """
        Sanitizes a string by escaping special characters.

        This is based on the escaping rules from the memegen project:
        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    A decorator that ensures a user is logged in before accessing a route.

    For more information, see the Flask documentation on view decorators:
    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Retrieves stock quote data for a given symbol."""
    url = f"https://finance.cs50.io/quote?symbol={symbol.upper()}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        quote_data = response.json()
        return {
            "name": quote_data["companyName"],
            "price": quote_data["latestPrice"],
            "symbol": symbol.upper()
        }
    except requests.RequestException:
        return None
    except (KeyError, ValueError):
        return None


def usd(value):
    """Converts a numeric value to a USD-formatted string."""
    return f"${value:,.2f}"