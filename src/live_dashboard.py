import time
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import oandapyV20
from oandapyV20 import API
from dotenv import load_dotenv
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments

st.set_page_config(
    layout="wide",
)
load_dotenv()

st.title("Real Time Trading Dashboard")


def parse_data_to_df(data):
    df_data = [
        {"time": candle["time"], "volume": candle["volume"], **candle["mid"]}
        for candle in data["candles"]
    ]
    new_df = pd.DataFrame(df_data)
    new_df["time"] = pd.to_datetime(new_df["time"])
    new_df[["o", "h", "l", "c", "volume"]] = new_df[
        ["o", "h", "l", "c", "volume"]
    ].apply(pd.to_numeric)
    new_df.rename(
        columns={"o": "open", "h": "high", "l": "low", "c": "close"}, inplace=True
    )
    return new_df


def fetch_candles(instrument, granularity, count):
    client = API(access_token=os.getenv("OANDA_ACCESS_TOKEN"))
    params = {"granularity": granularity, "count": count}
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    try:
        data = client.request(r)
        return parse_data_to_df(data)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()


def append_new_data(base_df, new_data):
    if not new_data.empty:
        # Check if the newest data's time is already in the base DataFrame
        if not base_df["time"].isin([new_data["time"].iloc[-1]]).any():
            return pd.concat([base_df, new_data], ignore_index=True)
    return base_df


r = instruments.InstrumentsCandles(
    instrument="USD_JPY", params={"granularity": "M1", "count": 200}
)


# read csv from a URL
# @st.cache_data
def get_data() -> pd.DataFrame:
    return fetch_candles("USD_JPY", "M1", 1000)


df = get_data()


# creating a single-element container
placeholder = st.empty()
while True:
    with placeholder.container():

        new_data = fetch_candles("USD_JPY", "M1", 1)

        df = pd.concat([df, new_data])
        df_tail = df.tail(100)
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df_tail["time"],
                    open=df_tail["open"],
                    high=df_tail["high"],
                    low=df_tail["low"],
                    close=df_tail["close"],
                )
            ]
        )
        fig.update_layout(
            title="Candlestick Chart of USD_JPY",
            title_x=0.5,
            title_y=1,
            xaxis_title="Date",
            yaxis_title="Closing Price",
            xaxis_showgrid=True,  # Add grid to x-axis
            yaxis_showgrid=True,  # Add grid to y-axis
            plot_bgcolor="rgba(0, 0, 0, 0)",  # Set plot background to transparent
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True, theme="streamlit")
        st.markdown("### Detailed Data View")
        st.dataframe(df_tail, use_container_width=True, hide_index=True)
        time.sleep(60)
