import os
from typing import Any, Dict, Union

import oandapyV20
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades
from dotenv import load_dotenv
from loguru import logger
from oandapyV20.exceptions import V20Error

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

    def get_open_positions(self) -> Dict[str, Any]:
        """
        Get open positions for the account.

        Returns:
            Dict[str, Any]: Open positions for the account
        """
        request = positions.OpenPositions(accountID=self.accountID)
        response = self.client.request(request)
        open_positions = response["positions"]
        return open_positions

    def get_current_price(self, instrument: str) -> float:
        """
        Get the latest bid price for an instrument.

        Args:
            instrument (str): currency pair

        Returns:
            float: price of the instrument
        """
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

    def get_buy_in_price(self, instrument: str) -> Union[float, None]:
        """
        Get the price at which the bot bought the instrument and convert
        to the required precision.

        Args:
            instrument (str): currency pair

        Returns:
            Union[float, None]: price at which the bot bought the
            instrument or None if not applicable
        """
        r = trades.OpenTrades(accountID=self.accountID)
        self.client.request(r)
        open_trades = r.response
        for trade in open_trades["trades"]:
            if trade["instrument"] == instrument:
                return round(float(trade["price"]), self.precision)
        return None

    def get_take_profit_price(self, instrument: str, units: int) -> float:
        """
        Get the take profit price for the instrument.

        Args:
            instrument (str): currency pair
            units (int): units to trade

        Raises:
            ValueError: if the instrument is invalid
            ValueError: if the entry price is not available

        Returns:
            float: take profit price
        """
        entry_price = self.get_current_price(instrument)
        if entry_price is None:
            raise ValueError("Could not retrieve the entry price")

        params = {"instruments": instrument}
        # checking pricing availability and if the instrument is currently tradeable
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

    def get_stop_loss_price(self, instrument: str, units: int) -> float:
        """
        Get the stop loss price for the instrument.

        Args:
            instrument (str): currency pair
            units (int): units to trade

        Raises:
            ValueError: if the instrument is invalid
            ValueError: if the entry price is not available

        Returns:
            float: stop loss price
        """
        entry_price = self.get_current_price(instrument)
        if entry_price is None:
            raise ValueError("Could not retrieve the entry price")

        params = {"instruments": instrument}
        # checking pricing availability and if the instrument is currently tradeable
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

    def place_market_order(self, instrument: str, units: int) -> None:
        """
        Place a market order for the instrument.

        Args:
            instrument (str): currency pair
            units (int): units to trade
        """
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
            logger.success(f"Oanda Orders placed successfully! Response: {response}")
        except V20Error as e:
            logger.error(f"Error placing Oanda orders:{e}")

    def place_limit_order(
        self,
        instrument: str,
        units: int,
        take_profit_price: float,
        stop_loss_price: float,
    ) -> None:
        """
        Place a conventional limit order when the agent takes a sell
        action.

        Args:
            instrument (str): currency pair
            units (int): units to trade
            take_profit_price (float): take profit price
            stop_loss_price (float): stop loss price

        Raises:
            ValueError: if the price is not available
        """
        try:
            current_price = self.get_current_price(instrument)
            if current_price is None:
                raise ValueError("Price not available")
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
            logger.error(f"Error getting pricing info:{e}")

        try:
            request = orders.OrderCreate(self.accountID, data=body)
            response = self.client.request(request)
            logger.success(f"Oanda Orders placed successfully! Response: {response}")
        except V20Error as e:
            logger.error(f"Error placing Oanda orders:{e}")

    def place_limit_order_take_profit(
        self,
        instrument: str,
        units: int,
        take_profit_price: float,
        stop_loss_price: float,
    ) -> None:
        """
        Place limit order to take profit even when the agent does not
        take a sell action.

        Args:
            instrument (str): currency pair
            units (int): units to trade
            take_profit_price (float): take profit price
            stop_loss_price (float): stop loss price
        """
        body = {
            "order": {
                "price": str(round(take_profit_price, self.precision)),
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

        try:
            request = orders.OrderCreate(self.accountID, data=body)
            response = self.client.request(request)
            logger.success(f"Oanda Orders placed successfully! Response: {response}")
        except V20Error as e:
            logger.error(f"Error placing Oanda orders:{e}")

    def place_limit_order_stop_loss(
        self,
        instrument: str,
        units: int,
        take_profit_price: float,
        stop_loss_price: float,
    ):
        body = {
            "order": {
                "price": str(round(stop_loss_price, self.precision)),
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

        try:
            request = orders.OrderCreate(self.accountID, data=body)
            response = self.client.request(request)
            logger.success(f"Oanda Orders placed successfully! Response: {response}")
        except V20Error as e:
            logger.error(f"Error placing Oanda orders:{e}")

    def close_all_trades(self) -> None:
        """Close all open trades for the account."""
        # Get a list of all open trades for the account
        trades_request = trades.OpenTrades(accountID=self.accountID)
        response = self.client.request(trades_request)

        if len(response["trades"]) > 0:
            for trade in response["trades"]:
                trade_id = trade["id"]
                try:
                    body = {
                        "units": "ALL",
                    }
                    order_request = trades.TradeClose(
                        accountID=self.accountID, tradeID=trade_id, data=body
                    )
                    response = self.client.request(order_request)
                    print(f"Trade {trade_id} closed successfully.")
                except oandapyV20.exceptions.V20Error as e:
                    print(f"Failed to close trade {trade_id}. Error: {e}")
        else:
            print("No open trades to close.")
