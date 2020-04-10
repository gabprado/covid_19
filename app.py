import pandas as pd
import os
import json
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, desc
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.environ.get("JAWSDB_URL", "") or "sqlite:///covid19.sqlite"
)
db = SQLAlchemy(app)

Base = automap_base()
Base.prepare(db.engine, reflect=True)

global_data = Base.classes.global_covid_data
us_data = Base.classes.us_covid_data
us_lookup = Base.classes.us_lookup
session = db.session


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
    us_confirmed = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"
    us_deaths = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv"
    global_cases = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
    global_deaths = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
    global_recovered = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv"

    us_confirmed_df = pd.read_csv(us_confirmed)
    us_deaths_df = pd.read_csv(us_deaths)
    global_cases_df = pd.read_csv(global_cases)
    global_deaths_df = pd.read_csv(global_deaths)
    global_recovered_df = pd.read_csv(global_recovered)

    def insert_to_db(table_name, df):
        # pri_key_qry = (
        #     f"ALTER TABLE `{table_name}` CHANGE COLUMN `ID` `ID` BIGINT NOT NULL"
        #     + ",ADD PRIMARY KEY (`ID`),ADD UNIQUE INDEX `ID_UNIQUE` (`ID` ASC) VISIBLE;"
        # )
        db.engine.execute(f"DROP TABLE IF EXISTS {table_name}")
        df.to_sql(name=table_name, con=db.engine, index_label="ID")
        # engine.execute(pri_key_qry)

    # get state mapping data
    states_data = pd.DataFrame(
        us_deaths_df[
            ["UID", "iso2", "Admin2", "Province_State", "Population", "Lat", "Long_"]
        ]
    ).rename(columns={"iso2": "Country_Abbrv", "Admin2": "County", "Long_": "Long"})

    # get us covid data
    us_cases_clean = pd.melt(
        us_confirmed_df.drop(
            columns=[
                "iso2",
                "iso3",
                "code3",
                "FIPS",
                "Admin2",
                "Province_State",
                "Country_Region",
                "Lat",
                "Long_",
                "Combined_Key",
            ]
        ),
        id_vars="UID",
        var_name="Date",
    ).rename(columns={"value": "Confirmed_Cases"})

    us_deaths_clean = pd.melt(
        us_deaths_df.drop(
            columns=[
                "iso2",
                "iso3",
                "code3",
                "FIPS",
                "Admin2",
                "Province_State",
                "Country_Region",
                "Lat",
                "Long_",
                "Combined_Key",
                "Population",
            ]
        ),
        id_vars="UID",
        var_name="Date",
    ).rename(columns={"value": "Deaths"})

    us_covid_data = pd.merge(
        us_cases_clean, us_deaths_clean, how="left", on=["UID", "Date"]
    ).fillna(0)
    # get global covid data
    global_cases_clean = pd.melt(
        global_cases_df,
        id_vars=["Province/State", "Country/Region", "Lat", "Long"],
        var_name="Date",
    ).rename(columns={"value": "Confirmed_Cases"})

    global_deaths_clean = pd.melt(
        global_deaths_df,
        id_vars=["Province/State", "Country/Region", "Lat", "Long"],
        var_name="Date",
    ).rename(columns={"value": "Deaths"})

    global_recovered_clean = pd.melt(
        global_recovered_df,
        id_vars=["Province/State", "Country/Region", "Lat", "Long"],
        var_name="Date",
    ).rename(columns={"value": "Recovered"})

    global_covid_data = (
        pd.merge(
            pd.merge(
                global_cases_clean,
                global_deaths_clean,
                how="left",
                on=["Province/State", "Country/Region", "Lat", "Long", "Date"],
            ),
            global_recovered_clean,
            how="left",
            on=["Province/State", "Country/Region", "Lat", "Long", "Date"],
        )
        .rename(
            columns={
                "Province/State": "Province_State",
                "Country/Region": "Country_Region",
            }
        )
        .fillna(0)
    )

    # import data
    insert_to_db("us_lookup", states_data)
    insert_to_db("us_covid_data", us_covid_data)
    insert_to_db("global_covid_data", global_covid_data)
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
        .order_by(global_data.Date)
    ).statement
    country_results = pd.read_sql_query(qry, db.engine)
    data = {
        "Date": country_results.Date.values.tolist(),
        "Confirmed_Cases": country_results.sum_1.values.tolist(),
        "Deaths": country_results.sum_2.values.tolist(),
        "Recovered": country_results.sum_3.values.tolist(),
    }
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
