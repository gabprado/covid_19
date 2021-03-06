import pandas as pd
import os
import json
from datetime import datetime, date
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, desc
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.environ.get("JAWSDB_URL", "") or "sqlite:///Stage/Data/covid19.sqlite"
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


@app.route("/sandbox")
def sandbox():
    result = render_template("sandbox.html")
    return result


@app.route("/country_list")
def get_country_list():
    qry = (
        session.query(global_data.Country_Region)
        .distinct()
        .order_by(global_data.Country_Region)
        .statement
    )
    df = pd.read_sql_query(qry, db.engine).rename(columns={"Country_Region": "Country"})
    data = {"Country": df.Country.values.tolist()}
    return jsonify(data)


@app.route("/global_data/<country>")
def get_country_data(country):
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
    ).statement
    df = pd.read_sql_query(qry, db.engine).rename(
        columns={
            "Country_Region": "Country",
            "sum_1": "Confirmed",
            "sum_2": "Deaths",
            "sum_3": "Recovered",
        }
    )
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values(by=["Date"])
    df["Deltas_Confirmed"] = df.Confirmed.diff()
    df["Five_Day_Avg_Confirmed"] = df.Deltas_Confirmed.rolling(window=5).mean()
    df["Deltas_Deaths"] = df.Deaths.diff()
    df["Five_Day_Avg_Deaths"] = df.Deltas_Deaths.rolling(window=5).mean()
    df["Deltas_Recovered"] = df.Recovered.diff()
    df["Five_Day_Avg_Recovered"] = df.Deltas_Recovered.rolling(window=5).mean()
    df = df.fillna(0)
    # get analysis fields
    first_case_df = df.loc[df["Confirmed"] > 0]
    first_case_df = first_case_df.head(1)
    current_state_df = df.tail(2)
    current_state_df[
        "Confirmed_Status"
    ] = current_state_df.Five_Day_Avg_Confirmed.diff()
    current_state_df["Deaths_Status"] = current_state_df.Five_Day_Avg_Deaths.diff()
    current_state_df[
        "Recovered_Status"
    ] = current_state_df.Five_Day_Avg_Recovered.diff()
    first_date = first_case_df.iloc[0, 1]
    days_since_first_case = (
        (datetime.strptime(current_state_df.iloc[1, 1], "%Y-%m-%d"))
        - (datetime.strptime(first_date, "%Y-%m-%d"))
    ).days
    confirmed_current = "{:,}".format(current_state_df.iloc[1, 2])
    deaths_current = "{:,}".format(int(current_state_df.iloc[1, 3]))
    recovered_current = "{:,}".format(int(current_state_df.iloc[1, 4]))
    confirmed_status = int(current_state_df.iloc[1, 11])
    summary = (
        f"The first case of COVID-19 in {country} was reported {days_since_first_case} days ago on "
        f"{datetime.strptime(first_date, '%Y-%m-%d').strftime('%B %d, %Y')}. "
        f"Since then, the country has reported {confirmed_current} cases, and {deaths_current} deaths. "
        f"The current number of recovered cases is {recovered_current}."
    )

    data = {
        "Date": df.Date.values.tolist(),
        "Confirmed_Cases": df.Confirmed.values.tolist(),
        "Deltas_Confirmed": df.Deltas_Confirmed.values.tolist(),
        "Five_Day_Avg_Confirmed": df.Five_Day_Avg_Confirmed.values.tolist(),
        "Deaths": df.Deaths.values.tolist(),
        "Deltas_Deaths": df.Deltas_Deaths.values.tolist(),
        "Five_Day_Avg_Deaths": df.Five_Day_Avg_Deaths.values.tolist(),
        "Recovered": df.Recovered.values.tolist(),
        "Deltas_Recovered": df.Deltas_Recovered.values.tolist(),
        "Five_Day_Avg_Recovered": df.Five_Day_Avg_Recovered.values.tolist(),
        "Analysis_Confirmed_Status": confirmed_status,
        "Analysis_Summary": summary,
    }
    return jsonify(data)


@app.route("/global_data")
def get_global_data():
    qry = (
        session.query(
            global_data.Country_Region,
            global_data.Date,
            func.sum(global_data.Confirmed_Cases),
            func.sum(global_data.Deaths),
            func.sum(global_data.Recovered),
        )
        .group_by(global_data.Country_Region, global_data.Date)
        .order_by(global_data.Date)
    ).statement
    df = (
        pd.read_sql_query(qry, db.engine)
        .rename(
            columns={
                "Country_Region": "Country",
                "sum_1": "Confirmed",
                "sum_2": "Deaths",
                "sum_3": "Recovered",
            }
        )
        .astype({"Confirmed": "int32", "Deaths": "int32", "Recovered": "int32"})
    )
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values(by="Date")
    data = {
        "Country": df.Country.values.tolist(),
        "Date": df.Date.values.tolist(),
        "Confirmed": df.Confirmed.values.tolist(),
        "Deaths": df.Deaths.values.tolist(),
        "Recovered": df.Recovered.values.tolist(),
    }
    return jsonify(data)


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
        db.engine.execute(f"DELETE FROM {table_name}")
        df.to_sql(name=table_name, con=db.engine, index_label="ID", if_exists="append")

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


if __name__ == "__main__":
    app.run(debug=True)
