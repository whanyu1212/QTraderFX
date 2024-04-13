import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import pandas as pd


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
        self.params = {"granularity": self.granularity, "count": self.count}

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch historical data from the OANDA API and process it into a
        dataframe.

        Returns:
            pd.DataFrame: dataframe containing the historical data
        """
        r = instruments.InstrumentsCandles(
            instrument=self.instrument, params=self.params
        )
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

    def check_columns(self, df: pd.DataFrame) -> None:
        """
        Check if the DataFrame contains the expected columns.

        Args:
            df (pd.DataFrame): input dataframe

        Raises:
            ValueError: if the DataFrame is missing one
            or more of the expected columns
        """
        expected_columns = ["Time", "High", "Close", "Low", "Open"]
        if not set(expected_columns).issubset(df.columns):
            raise ValueError(
                "DataFrame is missing one or more of ",
                f"the expected columns: {expected_columns}",
            )

    def convert_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert the 'Time' column to datetime format and set the
        timezone to avoid confusion.

        Args:
            df (pd.DataFrame): input dataframe

        Raises:
            ValueError: if the 'Time' column cannot be converted
            ValueError: if the 'Time' column is out of bounds

        Returns:
            pd.DataFrame: dataframe with the 'Time' column converted
        """
        try:
            df["Time"] = pd.to_datetime(df["Time"]).dt.tz_convert(self.timezone)
        except pd.errors.OutOfBoundsDatetime:
            raise ValueError(
                "Error converting 'Time' column to datetime: dates are out of bounds"
            )
        except Exception as e:
            raise ValueError(f"Error converting 'Time' column to datetime: {e}")
        return df

    def set_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Set the 'Time' column as the index of the DataFrame.

        Args:
            df (pd.DataFrame): input dataframe

        Returns:
            pd.DataFrame: dataframe with the 'Time' column as the index
        """
        df.set_index("Time", inplace=True)
        return df

    def convert_to_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert the 'High', 'Close', 'Low', and 'Open' columns to
        numeric.

        Args:
            df (pd.DataFrame): input dataframe

        Raises:
            ValueError: if the columns cannot be converted to numeric

        Returns:
            pd.DataFrame: dataframe with the columns converted to numeric
        """
        expected_columns = ["High", "Close", "Low", "Open"]
        try:
            df[expected_columns] = df[expected_columns].apply(pd.to_numeric)
        except Exception as e:
            raise ValueError(f"Error converting columns to numeric: {e}")
        return df

    def fetch_and_process_data(self) -> pd.DataFrame:
        """
        Chain the methods together to fetch and process the data.

        Returns:
            pd.DataFrame: processed dataframe
        """
        df = self.fetch_data()
        self.check_columns(df)
        df = self.convert_time(df)
        df = self.set_index(df)
        df = self.convert_to_numeric(df)
        return df
