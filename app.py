import pandas as pd
import json
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, desc
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from import_data import data_import, engine


app = Flask(__name__)
Base = automap_base()
Base.prepare(engine, reflect=True)
global_data = Base.classes.global_covid_data
us_data = Base.classes.us_covid_data
us_lookup = Base.classes.us_lookup
session = Session(engine)


@app.route("/")
def index():
    result = render_template("index.html")
    return result


@app.route("/country_snapshot")
def country_snapshot():
    result = render_template("country_snapshot.html")
    return result


@app.route("/import_data")
def import_data():
    data_import()
    return redirect(url_for("index"))


@app.route("/global_data/<country>/<data_point>")
def get_country_data(country, data_point):
    qry = (
        session.query(
            global_data.Country_Region,
            global_data.Date,
            func.sum(global_data.Confirmed_Cases),
            func.sum(global_data.Deaths),
            func.sum(global_data.Recovered),
        )
        .filter(global_data.Country_Region == country)
        .group_by(global_data.Country_Region, global_data.Date)
        .order_by(global_data.Country_Region)
    ).statement
    country_results = pd.read_sql_query(qry, engine)
    data = {
        "Date": country_results.Date.values.tolist(),
        "Confirmed_Cases": country_results.sum_1.values.tolist(),
        "Deaths": country_results.sum_2.values.tolist(),
        "Recovered": country_results.sum_3.values.tolist(),
    }
    # if data_point == "Deaths":
    #     col_idx = 3
    # elif data_point == "Recovered":
    #     col_idx = 4
    # else:
    #     col_idx = 2
    # country_results = (
    # session.query(
    #     global_data.Country_Region,
    #     global_data.Date,
    #     func.sum(global_data.Confirmed_Cases),
    #     func.sum(global_data.Deaths),
    #     func.sum(global_data.Recovered)
    # ).filter(global_data.Country_Region == country)
    #  .group_by(global_data.Country_Region, global_data.Date)
    # .order_by(global_data.Country_Region)
    # ).all()
    # country_dict = [{"Date": rec[1], data_point: int(rec[col_idx])} for rec in country_results]
    return jsonify(data)


@app.route("/global_data")
def get_global_data():
    countries = (
        session.query(global_data.Country_Region)
        .distinct()
        .order_by(global_data.Country_Region)
        .all()
    )
    global_covid_results = (
        session.query(
            global_data.Country_Region,
            global_data.Date,
            func.sum(global_data.Confirmed_Cases),
            func.sum(global_data.Deaths),
            func.sum(global_data.Recovered),
        )
        .group_by(global_data.Country_Region, global_data.Date)
        .order_by(global_data.Country_Region)
    ).all()

    def get_country_covid_data(country):
        data = {}
        for rec in global_covid_results:
            if rec[0] == country:
                data[rec[1]] = {
                    "Confirmed_Cases": int(rec[2]),
                    "Deaths": int(rec[3]),
                    "Recovered": int(rec[4]),
                }
        return data

    global_dict = [
        {"Country": country[0], "Data": get_country_covid_data(country[0])}
        for country in countries
    ]

    return jsonify(global_dict)


if __name__ == "__main__":
    app.run(debug=True)
