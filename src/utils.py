import pandas as pd
import yaml


def parse_yml(path):
    with open(path, "r") as file:
        data = yaml.safe_load(file)
    return data


def process_streaming_response(response, temp_list):
    bid = float(response["closeoutBid"])
    ask = float(response["closeoutAsk"])
    mid = round((bid + ask) / 2, 3)
    temp_list.append(mid)


def get_candlestick_data(time, temp_list):
    open = round(temp_list[0], 3)
    high = round(max(temp_list), 3)
    low = round(min(temp_list), 3)
    close = round(temp_list[-1], 3)

    data = {"Open": open, "High": high, "Low": low, "Close": close}
    df = pd.DataFrame(data, index=[time])

    return df


def calculate_indicators(df):

    # SMA
    df["SMA"] = df["Close"].rolling(window=5).mean()

    # RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(span=5).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=5).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    df["MACD"] = df["Close"].ewm(span=5).mean() - df["Close"].ewm(span=13).mean()

    # Stochastic Oscillator
    low_5, high_5 = (
        df["Low"].rolling(window=5).min(),
        df["High"].rolling(window=5).max(),
    )
    df["%K"] = 100 * (df["Close"] - low_5) / (high_5 - low_5)
    df["%D"] = df["%K"].rolling(window=3).mean()

    return df