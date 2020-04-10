import pandas as pd
import csv
import json
from sqlalchemy import create_engine


engine = create_engine(JAWSDB_URL)
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
    pri_key_qry = (
        f"ALTER TABLE `{table_name}` CHANGE COLUMN `ID` `ID` BIGINT NOT NULL"
        + ",ADD PRIMARY KEY (`ID`),ADD UNIQUE INDEX `ID_UNIQUE` (`ID` ASC) VISIBLE;"
    )
    engine.execute(f"DROP TABLE IF EXISTS {table_name}")
    df.to_sql(name=table_name, con=engine, index_label="ID")
    engine.execute(pri_key_qry)


def get_state_info():
    states_data = pd.DataFrame(
        us_deaths_df[
            ["UID", "iso2", "Admin2", "Province_State", "Population", "Lat", "Long_"]
        ]
    ).rename(columns={"iso2": "Country_Abbrv", "Admin2": "County", "Long_": "Long"})
    return states_data


def get_us_covid_info():
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
    return us_covid_data


def get_global_info():
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
    return global_covid_data


def data_import():
    insert_to_db("us_lookup", get_state_info())
    insert_to_db("us_covid_data", get_us_covid_info())
    insert_to_db("global_covid_data", get_global_info())
