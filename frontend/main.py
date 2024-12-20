# Make a simple Flask app that serves the frontend

import datetime
from flask import Flask, render_template, redirect, request
from frontend.database import Database


app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers["X-Version"] = "0.3.0"
    return response

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query")

    if not query:
        return redirect("/")
    

    start_time = datetime.datetime.now()
    results = Database().search(query)
    return render_template("search.html", query=query, results=results, human_readable_time_interval_seconds=(datetime.datetime.now() - start_time).total_seconds())

@app.route("/feeling-lucky", methods=["GET"])
def feeling_lucky():

    return redirect("https://github.com/Om-Mishra7/gibble", code=302)

if __name__ == "__main__":
    app.run()
    
    