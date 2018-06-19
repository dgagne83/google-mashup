import os
import re
from flask import Flask, jsonify, render_template, request, url_for
from flask_jsglue import JSGlue

import sqlite3
# from cs50 import SQL
from helpers import lookup

# configure application
app = Flask(__name__)
JSGlue(app)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure CS50 Library to use SQLite database
# db = SQL("sqlite:///mashup.db")


@app.route("/")
def index():
    """Render map."""
    if not os.environ.get("API_KEY"):
        raise RuntimeError("API_KEY not set")
    return render_template("index.html", key=os.environ.get("API_KEY"))

@app.route("/articles")
def articles():
    """Look up articles for geo."""
    location = request.args.get("geo")

    """Ensure a geo is in the URL"""
    if not location:
        raise RuntimeError("No geo entered")

    # return the JSON list of articles and links
    return jsonify(lookup(location))

@app.route("/search")
def search():
    """Search for places that match query."""
    location = request.args.get("q")
    conn = sqlite3.connect('mashup.db')
    db = conn.cursor()

    """Ensure a geo is in the URL"""
    if not location:
        raise RuntimeError("No q entered")

    """allow for entry of city, county, state or comma separated entry of a mix city/county/state"""
    if ',' in location:
        mylist = location.split(', ')
        city_state = [
            ("%" + mylist[0] + "%", "%" + mylist[1] + "%"),
            ("%" + mylist[0] + "%", "%" + mylist[1] + "%"),
            ("%" + mylist[0] + "%", "%" + mylist[1] + "%"),
            ("%" + mylist[0] + "%", "%" + mylist[1] + "%"),
        ]
        result = db.execute("SELECT * FROM places \
                             WHERE (place_name LIKE ? AND admin_name1 LIKE ?) \
                             OR (place_name LIKE ? AND admin_code1 LIKE ?) \
                             OR (admin_name2 LIKE ? AND admin_code1 LIKE ?) \
                             OR (admin_name2 LIKE ? AND admin_code1 LIKE ?) \
                             OR (place_name LIKE ? AND admin_name2 LIKE ?)", city_state)

        return jsonify(result)
    else:
        sql_location = (
            "%" + location + "%",
            "%" + location + "%",
            "%" + location + "%",
            "%" + location + "%",
            "%" + location + "%",
        )
        result = db.execute("SELECT * FROM places \
                             WHERE postal_code LIKE ? \
                             OR place_name LIKE ? \
                             OR admin_name2 LIKE ? \
                             OR admin_name1 LIKE ? \
                             OR admin_code1 LIKE ?", )
        return jsonify(result.fetchall())
    conn.close()

@app.route("/update")
def update():
    """Find up to 10 places within view."""
    conn = sqlite3.connect('mashup.db')
    db = conn.cursor()

    # ensure parameters are present
    if not request.args.get("sw"):
        raise RuntimeError("missing sw")
    if not request.args.get("ne"):
        raise RuntimeError("missing ne")

    # ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
        raise RuntimeError("invalid ne")

    # explode southwest corner into two variables
    (sw_lat, sw_lng) = [float(s) for s in request.args.get("sw").split(",")]

    # explode northeast corner into two variables
    (ne_lat, ne_lng) = [float(s) for s in request.args.get("ne").split(",")]

    # find 10 cities within view, pseudorandomly chosen if more within view
    if (sw_lng <= ne_lng):

        # doesn't cross the antimeridian
        rows = db.execute("""SELECT * FROM places
            WHERE ? <= latitude AND latitude <= ? AND (? <= longitude AND longitude <= ?)
            GROUP BY country_code, place_name, admin_code1
            ORDER BY RANDOM()
            LIMIT 10""",
            (sw_lat, ne_lat, sw_lng, ne_lng))

    else:

        # crosses the antimeridian
        rows = db.execute("""SELECT * FROM places
            WHERE ? <= latitude AND latitude <= ? AND (? <= longitude OR longitude <= ?)
            GROUP BY country_code, place_name, admin_code1
            ORDER BY RANDOM()
            LIMIT 10""",
            (sw_lat, ne_lat, sw_lng, ne_lng))

    # output places as JSON
    return jsonify(rows.fetchall())
    conn.close()
