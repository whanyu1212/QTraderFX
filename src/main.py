import pandas as pd
import numpy as np
from loguru import logger
from oandapyV20 import API
from src.fetch_historical_data import FetchHistoricalData
from src.streaming_pipeline import StreamingDataPipeline
from src.utils import parse_yml, calculate_indicators
from dotenv import load_dotenv
import os

load_dotenv()


# Global variables
accountID = os.getenv("OANDA_ACCOUNT_ID")
token = os.getenv("OANDA_ACCESS_TOKEN")


def get_config(path):
    return parse_yml(path)


def fetch_historical_candles(cfg):
    fetcher = FetchHistoricalData(
        cfg["candlestick"]["instrument"],
        cfg["candlestick"]["granularity"],
        token,
        cfg["candlestick"]["count"],
    )
    df = fetcher.fetch_data()
    df = fetcher.process_data(df)
    return df


def start_streaming_pipeline(cfg, df):
    api = API(access_token=token)
    params = {"instruments": cfg["pricingstream"]["instrument"]}
    pipeline = StreamingDataPipeline(accountID, params, api, df)
    pipeline.run()


def main():
    logger.info("Starting the pipeline...")
    cfg = get_config("./cfg/parameters.yaml")
    df = calculate_indicators(fetch_historical_candles(cfg))
    df.dropna(inplace=True)
    logger.success(f"Historical candlestick data fetched successfully:\n{df.tail()}")
    start_streaming_pipeline(cfg, df)
    logger.info("Pipeline completed.")


if __name__ == "__main__":
    main()
