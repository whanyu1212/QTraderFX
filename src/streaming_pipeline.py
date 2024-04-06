import pandas as pd
import oandapyV20
import oandapyV20.endpoints.pricing as pricing
from oandapyV20 import API
from datetime import datetime, timedelta
from termcolor import colored
from src.q_learning import QLearningTrader
from src.orders import (
    get_open_positions,
    get_take_profit_price,
    get_stop_loss_price,
    place_market_order,
    place_limit_order,
    close_all_trades,
)
from src.utils import (
    process_streaming_response,
    get_candlestick_data,
    calculate_indicators,
)


class StreamingDataPipeline:
    def __init__(self, accountID, params, api, df):
        self.accountID = accountID
        self.params = params
        self.api = api
        self.df = df
        self.start_time = datetime.now()
        self.max_duration = timedelta(minutes=10)
        self.interval_start = datetime.now()
        self.interval = timedelta(minutes=1)
        self.temp_list = []
        self.qtrader = QLearningTrader(
            num_actions=3,
            num_features=9,
            learning_rate=0.01,
            discount_factor=0.9,
            exploration_prob=0.1,
        )

    def check_max_duration(self):
        if datetime.now() - self.start_time >= self.max_duration:
            print("Maximum duration reached, exiting...")
            return True
        return False

    def process_tick(self, tick):
        process_streaming_response(tick, self.temp_list)
        print(
            f"Time: {tick['time']}, {colored('closeoutBid:', 'green')} {tick['closeoutBid']}, {colored('closeoutAsk:', 'red')} {tick['closeoutAsk']}"
        )
        print()
        if datetime.now() - self.interval_start >= self.interval:
            self.interval_start = datetime.now()
            if self.temp_list:
                new_df = get_candlestick_data(self.interval_start, self.temp_list)
                action = self.qtrader.update(self.df, new_df)
                positions = get_open_positions(self.accountID, self.api)
                if action == 0 and not positions:
                    print(f"Stop loss price: {stoplossprice}")
                    print(f"Take profit price: {takeprofitprice}")
                    print("Placing market order...")
                    place_market_order(
                        self.api,
                        self.accountID,
                        self.params["instruments"],
                        1000,
                    )
                    print()

                if action == 1 and positions:
                    print("Closing all open positions...")
                    stoplossprice = get_stop_loss_price(
                        self.api,
                        self.accountID,
                        self.params["instruments"],
                        -1000,
                        0.02,
                    )
                    takeprofitprice = get_take_profit_price(
                        self.api,
                        self.accountID,
                        self.params["instruments"],
                        -1000,
                        0.02,
                    )
                    print(f"Stop loss price: {stoplossprice}")
                    print(f"Take profit price: {takeprofitprice}")
                    print("Selling market order...")
                    place_limit_order(
                        self.api,
                        self.accountID,
                        self.params["instruments"],
                        -1000,
                        takeprofitprice,
                        stoplossprice,
                    )
                    print()
                    # close_all_positions(self.api, self.accountID)
                else:
                    print("No action taken.")
                self.df = pd.concat([self.df, new_df])
                self.temp_list.clear()
                self.df = calculate_indicators(self.df)
                print(self.df.tail(5))
                print()

    def run(self):
        self.qtrader.train(self.df)
        print()
        r = pricing.PricingStream(accountID=self.accountID, params=self.params)
        try:
            rv = self.api.request(r)
            for tick in rv:
                if self.check_max_duration():
                    close_all_trades(self.api, self.accountID)
                    break
                try:
                    self.process_tick(tick)
                except Exception as e:
                    print(
                        colored(
                            "Processing heartbeat messages for network latency check",
                            "blue",
                        )
                    )
        except oandapyV20.exceptions.V20Error as err:
            print(f"V20Error encountered: {err}")
        except KeyboardInterrupt:
            print("Streaming stopped by user.")
        finally:
            return self.df
