import concurrent.futures
import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Tuple

import oandapyV20.endpoints.accounts as accounts
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from oandapyV20 import API
from termcolor import colored

from src.fetch_historical_data import FetchHistoricalData
from src.streaming_pipeline import StreamingDataPipeline
from src.utils import calculate_indicators, parse_yml

load_dotenv()


# Global variables
accountID = os.getenv("OANDA_ACCOUNT_ID")
token = os.getenv("OANDA_ACCESS_TOKEN")


def get_account_summary() -> None:
    """Print the account summary before starting the pipeline."""
    client = API(access_token=token)
    r = accounts.AccountSummary(accountID)
    client.request(r)
    account_info = r.response["account"]
    print(
        colored("Account ID: ", "green")
        + f"{account_info['id']}"
        + "\n"
        + colored("Account Balance: ", "green")
        + f"{account_info['balance']}"
        + "\n"
        + f"As of: {datetime.datetime.now()}"
    )


def fetch_historical_candles(cfg: Dict, instrument: str) -> pd.DataFrame:
    """
    Fetch historical candlestick data from the OANDA API and process it
    into a DataFrame, to be used for training.

    Args:
        cfg (Dict): configuration dictionary
        instrument (str): currency pair to fetch data for

    Returns:
        pd.DataFrame: DataFrame containing the historical data
    """
    fetcher = FetchHistoricalData(
        instrument,
        cfg["candlestick"]["granularity"],
        token,
        cfg["candlestick"]["count"],
    )
    df = fetcher.fetch_and_process_data()
    return df


def start_streaming_pipeline(
    instrument: str,
    df: pd.DataFrame,
    precision: int,
    stop_loss: float,
    take_profit: float,
):
    """
    Execute the real time streaming pipeline for trading the selected
    currency pair.

    Args:
        instrument (str): currency pair to trade
        df (pd.DataFrame): historical candlestick data
        precision (int): number of decimal places
        stop_loss (float): stop loss value
        take_profit (float): take profit value
    """
    client = API(access_token=token)
    params = {"instruments": instrument}
    pipeline = StreamingDataPipeline(
        accountID, params, client, df, precision, stop_loss, take_profit
    )
    pipeline.run()


def select_currency_pair(round_number: int) -> str:
    """
    Take user input to select the currency pairs.

    Args:
        round_number (int): round number

    Returns:
        str: a string representing the selected currency pair
    """
    print(f"Select the currency pair to trade in round {round_number}:")
    print("1: EUR/USD")
    print("2: AUD/USD")
    print("3: NZD/USD")
    print("4: GBP/USD")
    print("5: GBP/JPY")
    print("6: USD/JPY")
    print("7: EUR/JPY")

    currency_pair = input("Enter the number corresponding to your choice: ")

    if currency_pair == "1":
        return "EUR_USD"
    elif currency_pair == "2":
        return "AUD_USD"
    elif currency_pair == "3":
        return "NZD_USD"
    elif currency_pair == "4":
        return "GBP_USD"
    elif currency_pair == "5":
        return "GBP_JPY"
    elif currency_pair == "6":
        return "USD_JPY"
    elif currency_pair == "7":
        return "EUR_JPY"
    else:
        print("Invalid selection. Defaulting to EUR/USD.")
        return "EUR_USD"


def get_instrument_config(
    cfg: Dict[str, Dict[str, float]], instrument: str
) -> Tuple[float, float, float]:
    precision = cfg["instrument_precision"][instrument]
    stoploss = cfg["stop_loss"][instrument]
    takeprofit = cfg["take_profit"][instrument]
    return precision, stoploss, takeprofit


def start_pipeline_in_concurrent_executor(
    executor: ThreadPoolExecutor,
    instrument: str,
    df: pd.DataFrame,
    precision: int,
    stoploss: float,
    takeprofit: float,
) -> Any:
    """
    Start the pipeline in a concurrent executor.

    Args:
        executor (ThreadPoolExecutor): multithreading executor
        instrument (str): currency pair to trade
        df (pd.DataFrame): historical candlestick data
        precision (int): number of decimal places
        stoploss (float): stop loss value
        takeprofit (float): take profit value

    Returns:
        Any: result of the pipeline execution,
        not compulsory to return anything
    """
    future = executor.submit(
        start_streaming_pipeline,
        instrument,
        df,
        precision,
        stoploss,
        takeprofit,
    )
    try:
        result = future.result()
    except Exception as e:
        print(f"An exception occurred: {e}")
    return result


def main():
    """Main function to run the pipeline from end to end."""

    logger.info("Starting the pipeline...")
    cfg = parse_yml("./cfg/parameters.yaml")

    # Get account summary before starting the pipeline
    get_account_summary()
    time.sleep(2)

    instrument1 = select_currency_pair(1)
    instrument2 = select_currency_pair(2)

    while instrument1 == instrument2:
        print("Duplicate pairs are not allowed. Please select again.")
        instrument2 = select_currency_pair(2)

    print(f"Selected currency pairs are : {instrument1}, {instrument2}")

    precision_1, stoploss_1, takeprofit_1 = get_instrument_config(cfg, instrument1)
    precision_2, stoploss_2, takeprofit_2 = get_instrument_config(cfg, instrument2)

    df_1 = calculate_indicators(fetch_historical_candles(cfg, instrument1)).dropna(
        inplace=False
    )
    df_2 = calculate_indicators(fetch_historical_candles(cfg, instrument2)).dropna(
        inplace=False
    )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        start_pipeline_in_concurrent_executor(
            executor, instrument1, df_1, precision_1, stoploss_1, takeprofit_1
        )
        start_pipeline_in_concurrent_executor(
            executor, instrument2, df_2, precision_2, stoploss_2, takeprofit_2
        )
    logger.info("Pipeline completed.")


if __name__ == "__main__":
    main()
