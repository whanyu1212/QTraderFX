from datetime import datetime
from typing import Dict, List

import pandas as pd
import yaml


def parse_yml(path: str) -> Dict:
    """
    Parse a yaml file and return a dictionary.

    Args:
        path (str): path to the yaml

    Returns:
        Dict: Dict that contains the content
        of the yaml file
    """
    with open(path, "r") as file:
        data = yaml.safe_load(file)
    return data


def process_streaming_response(response: Dict, temp_list: List[float]):
    """
    Derive the mid price from the response and append it to the
    temp_list.

    Args:
        response (Dict): response from API
        temp_list (List[float]): list for storing
    """
    bid = float(response["closeoutBid"])
    ask = float(response["closeoutAsk"])
    mid = (bid + ask) / 2
    temp_list.append(mid)


def get_candlestick_data(time: datetime, temp_list: List[float]) -> pd.DataFrame:
    """
    Derive candlestick data from the temp_list.

    Args:
        time (datetime): current time
        temp_list (List[float]): list that stores the mid prices

    Returns:
        pd.DataFrame: dataframe that contains the candlestick data
    """
    open = temp_list[0]
    high = max(temp_list)
    low = min(temp_list)
    close = temp_list[-1]

    data = {"Open": open, "High": high, "Low": low, "Close": close}
    df = pd.DataFrame(data, index=[time])

    return df


def calculate_sma(df: pd.DataFrame, SMA_WINDOW: int = 5) -> pd.DataFrame:
    """
    Calculate the Simple Moving Average (SMA) over a specified window.

    Args:
        df (pd.DataFrame): input dataframe that contains
        candlestick data
        SMA_WINDOW (int, optional): Specified window size.
        Defaults to 5.

    Returns:
        pd.DataFrame: dataframe with the SMA column appended
    """
    df["SMA"] = df["Close"].rolling(window=SMA_WINDOW).mean()
    return df


def calculate_rsi(df: pd.DataFrame, RSI_SPAN: int = 5) -> pd.DataFrame:
    """
    Calculate the Relative Strength Index (RSI)

    Args:
        df (pd.DataFrame): input dataframe that contains
        candlestick data
        RSI_SPAN (int, optional): rsi span. Defaults to 5.

    Returns:
        pd.DataFrame: dataframe with the RSI column appended
    """
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(span=RSI_SPAN).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=RSI_SPAN).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def calculate_macd(
    df: pd.DataFrame, short_window: int = 5, long_window: int = 13
) -> pd.DataFrame:
    """
    Calculate the Moving Average Convergence Divergence (MACD)

    Args:
        df (pd.DataFrame): input dataframe that contains
        candlestick data
        short_window (int, optional): short window size. Defaults to 5.
        long_window (int, optional): long window size. Defaults to 13.

    Returns:
        pd.DataFrame: dataframe with the MACD column appended
    """
    df["MACD"] = (
        df["Close"].ewm(span=short_window).mean()
        - df["Close"].ewm(span=long_window).mean()
    )
    return df


def calculate_stochastic_oscillator(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Calculate the Stochastic Oscillator.

    Args:
        df (pd.DataFrame): input dataframe that contains
        candlestick data
        window (int, optional): window size. Defaults to 5.

    Returns:
        pd.DataFrame: dataframe with the %K and %D columns appended
    """
    low_5, high_5 = (
        df["Low"].rolling(window=window).min(),
        df["High"].rolling(window=window).max(),
    )
    df["%K"] = 100 * (df["Close"] - low_5) / (high_5 - low_5)
    df["%D"] = df["%K"].rolling(window=3).mean()
    return df


def calculate_support_resistance(
    df: pd.DataFrame, window_size: int = 5, multiplier: float = 0.5
) -> pd.DataFrame:
    """
    Calculate the support and resistance levels.

    Args:
        df (pd.DataFrame): input dataframe that contains
        candlestick data
        window_size (int, optional): window size. Defaults to 5.
        multiplier (float, optional): multiplier. Defaults to 0.5.

    Returns:
        pd.DataFrame: dataframe with the support and resistance columns appended
    """
    df["resistance"] = (
        df["Close"].rolling(window=window_size).mean()
        + multiplier * df["Close"].rolling(window=window_size).std()
    )

    df["support"] = (
        df["Close"].rolling(window=window_size).mean()
        - multiplier * df["Close"].rolling(window=window_size).std()
    )

    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the technical indicators needed to feed into the trading
    strategy.

    Args:
        df (pd.DataFrame): input dataframe that contains
        candlestick data

    Returns:
        pd.DataFrame: dataframe with the technical indicators
        appended
    """
    df = calculate_sma(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_stochastic_oscillator(df)
    df = calculate_support_resistance(df)

    return df
