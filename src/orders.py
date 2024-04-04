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


def get_take_profit_price(instrument, units, entry_price, take_profit_pips):
    client = API(access_token=token)
    params = {"instruments": instrument}
    request = pricing.PricingInfo(accountID=accountID, params=params)
    response = client.request(request)
    prices = response["prices"][0]
    if instrument in prices["instrument"]:
        if units > 0:
            take_profit_price = entry_price + take_profit_pips
        else:
            take_profit_price = entry_price - take_profit_pips
        return take_profit_price
    else:
        raise ValueError(f"Invalid instrument: {instrument}")


def get_stop_loss_price(instrument, units, entry_price, stop_loss_pips):
    client = API(access_token=token)
    params = {"instruments": instrument}
    request = pricing.PricingInfo(accountID=accountID, params=params)
    response = client.request(request)
    prices = response["prices"][0]
    if instrument in prices["instrument"]:
        if units > 0:
            stop_loss_price = entry_price - stop_loss_pips
        else:
            stop_loss_price = entry_price + stop_loss_pips
        return stop_loss_price
    else:
        raise ValueError(f"Invalid instrument: {instrument}")


def place_market_order(
    accountID, instrument, units, take_profit_price, stop_loss_price
):
    client = API(access_token=token)
    data = {
        "order": {
            "units": str(units),
            "instrument": instrument,
            "timeInForce": "FOK",
            "type": "LIMIT",
            "positionFill": "DEFAULT",
            "takeProfitOnFill": {
                "price": str(float(take_profit_price)),
            },
            "stopLossOnFill": {
                "price": str(float(stop_loss_price)),
            },
        }
    }
    try:
        request = orders.OrderCreate(accountID, data=data)
        response = client.request(request)
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
