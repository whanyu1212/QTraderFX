import oandapyV20
from oandapyV20 import API
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.endpoints.accounts import AccountDetails
from oandapyV20.exceptions import V20Error
from dotenv import load_dotenv
import os

load_dotenv()

accountID = os.getenv("OANDA_ACCOUNT_ID")
token = os.getenv("OANDA_ACCESS_TOKEN")


class TradingBot:
    def __init__(
        self,
        client,
        accountID,
        precision,
        stop_loss_pips,
        take_profit_pips,
    ):
        self.client = client
        self.accountID = accountID
        self.precision = precision
        self.stop_loss_pips = stop_loss_pips
        self.take_profit_pips = take_profit_pips

    def get_open_positions(self):
        request = positions.OpenPositions(accountID=self.accountID)
        response = self.client.request(request)
        open_positions = response["positions"]
        return open_positions

    def get_current_price(self, instrument):
        params = {"instruments": instrument}
        try:
            request = pricing.PricingInfo(accountID=self.accountID, params=params)
            response = self.client.request(request)

            if "prices" in response and response["prices"]:
                return float(response["prices"][0]["bids"][0]["price"])
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

        return None

    def get_take_profit_price(self, instrument, units):
        entry_price = self.get_current_price(instrument)
        if entry_price is None:
            raise ValueError("Could not retrieve the entry price")

        params = {"instruments": instrument}
        request = pricing.PricingInfo(accountID=self.accountID, params=params)
        response = self.client.request(request)
        prices = response["prices"][0]
        if instrument in prices["instrument"]:
            if units > 0:
                take_profit_price = entry_price + self.take_profit_pips
            else:
                take_profit_price = entry_price - self.take_profit_pips
            return round(take_profit_price, self.precision)
        else:
            raise ValueError(f"Invalid instrument: {instrument}")

    def get_stop_loss_price(self, instrument, units):
        entry_price = self.get_current_price(instrument)
        if entry_price is None:
            raise ValueError("Could not retrieve the entry price")

        params = {"instruments": instrument}
        request = pricing.PricingInfo(accountID=self.accountID, params=params)
        response = self.client.request(request)
        prices = response["prices"][0]
        if instrument in prices["instrument"]:
            if units > 0:
                stop_loss_price = entry_price - self.stop_loss_pips
            else:
                stop_loss_price = entry_price + self.stop_loss_pips
            return round(stop_loss_price, self.precision)
        else:
            raise ValueError(f"Invalid instrument: {instrument}")

    def place_market_order(self, instrument, units):
        body = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
            }
        }

        try:
            request = orders.OrderCreate(self.accountID, data=body)
            response = self.client.request(request)
            print("Oanda Orders placed successfully!")
            subject = "Oanda Trades Initiated"
            body = "Oanda Trades Initiated"
            # send_email_notification(subject, body)
        except V20Error as e:
            print("Error placing Oanda orders:")
            print(e)
            subject = "Failed to Take Oanda Trades"
            body = "Failed to Take Oanda Trades"

    def place_limit_order(self, instrument, units, take_profit_price, stop_loss_price):
        try:
            current_price = self.get_current_price(instrument)
            if current_price is None:
                raise ValueError("Current price is None")
            body = {
                "order": {
                    "price": str(round(current_price, self.precision)),
                    "units": str(units),
                    "instrument": instrument,
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "positionFill": "DEFAULT",
                    "takeProfitOnFill": {
                        "price": str(round(take_profit_price, self.precision)),
                    },
                    "stopLossOnFill": {
                        "price": str(round(stop_loss_price, self.precision)),
                    },
                }
            }
        except Exception as e:
            print("Error:", e)

        try:
            request = orders.OrderCreate(self.accountID, data=body)
            response = self.client.request(request)
            print("Oanda Orders placed successfully!")
            subject = "Oanda Trades Initiated"
            body = "Oanda Trades Initiated"
            # send_email_notification(subject, body)
        except V20Error as e:
            print("Error placing Oanda orders:")
            print(e)
            subject = "Failed to Take Oanda Trades"
            body = "Failed to Take Oanda Trades"
            # send_email_notification(subject, body)

    def close_all_trades(self):
        # Get a list of all open trades for the account
        trades_request = trades.OpenTrades(accountID=self.accountID)
        response = self.client.request(trades_request)

        if len(response["trades"]) > 0:
            for trade in response["trades"]:
                trade_id = trade["id"]
                try:
                    # Create a market order to close the trade
                    data = {
                        "units": "ALL",
                    }
                    order_request = trades.TradeClose(
                        accountID=self.accountID, tradeID=trade_id, data=data
                    )
                    response = self.client.request(order_request)
                    print(f"Trade {trade_id} closed successfully.")
                except oandapyV20.exceptions.V20Error as e:
                    print(f"Failed to close trade {trade_id}. Error: {e}")
        else:
            print("No open trades to close.")
