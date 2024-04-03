import oandapyV20
import pandas as pd
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments


class FetchHistoricalData:
    def __init__(
        self, instrument, granularity, token, count=5000, timezone="Asia/Singapore"
    ):
        self.instrument = instrument
        self.granularity = granularity
        self.count = count
        self.token = token
        self.timezone = timezone
        self.client = oandapyV20.API(access_token=self.token)

    def fetch_data(self):
        params = {"granularity": self.granularity, "count": self.count}
        r = instruments.InstrumentsCandles(instrument=self.instrument, params=params)
        self.client.request(r)

        data = [
            {
                "Time": d["time"],
                "High": d["mid"]["h"],
                "Close": d["mid"]["c"],
                "Low": d["mid"]["l"],
                "Open": d["mid"]["o"],
            }
            for d in r.response["candles"]
        ]

        df = pd.DataFrame(data)
        return df

    def process_data(self, df):
        expected_columns = ["Time", "High", "Close", "Low", "Open"]

        if not set(expected_columns).issubset(df.columns):
            raise ValueError(
                f"DataFrame is missing one or more of the expected columns: {expected_columns}"
            )

        try:
            df["Time"] = pd.to_datetime(df["Time"]).dt.tz_convert(self.timezone)
        except Exception as e:
            raise ValueError(f"Error converting 'Time' column to datetime: {e}")

        df.set_index("Time", inplace=True)

        try:
            df[expected_columns[1:]] = df[expected_columns[1:]].apply(pd.to_numeric)
        except Exception as e:
            raise ValueError(f"Error converting columns to numeric: {e}")

        return df

    def flow(self):
        df = self.fetch_data()
        df = self.process_data(df)
        return df
