import pandas as pd
import oandapyV20
import oandapyV20.endpoints.pricing as pricing
from datetime import datetime, timedelta
from termcolor import colored
from src.q_learning import QLearningTrader
from src.trading_bot import TradingBot


from src.utils import (
    process_streaming_response,
    get_candlestick_data,
    calculate_indicators,
)


class StreamingDataPipeline:
    ACTION_BUY = 0
    ACTION_SELL = 1
    ACTION_HOLD = 2
    ORDER_SIZE = 100000

    def __init__(
        self,
        accountID,
        params,
        client,
        df,
        precision,
        stop_loss_pips,
        take_profit_pips,
    ):
        self.accountID = accountID
        self.params = params
        self.client = client
        self.df = df
        self.start_time = datetime.now()
        self.max_duration = timedelta(minutes=300)
        self.interval_start = datetime.now()
        self.interval = timedelta(minutes=1)
        self.temp_list = []
        self.qtrader = QLearningTrader(
            num_actions=3,
            num_features=11,
            learning_rate=0.01,
            discount_factor=0.9,
            exploration_prob=0.1,
        )
        self.bot = TradingBot(
            client,
            accountID,
            precision,
            stop_loss_pips,
            take_profit_pips,
        )

    def check_max_duration(self):
        if datetime.now() - self.start_time >= self.max_duration:
            print("Maximum duration reached, exiting...")
            return True
        return False

    def handle_buy_action(self):
        print("Action is 0 and no open positions...")
        print("Placing market order to buy...")
        self.bot.place_market_order(self.params["instruments"], self.ORDER_SIZE)
        print()

    def handle_sell_action(self):
        print("Action is 1 and there are open positions...")
        print("Placing limit order to sell...")
        # stoplossprice = self.bot.get_stop_loss_price(
        #     self.params["instruments"], -self.ORDER_SIZE
        # )
        # takeprofitprice = self.bot.get_take_profit_price(
        #     self.params["instruments"], -self.ORDER_SIZE
        # )
        self.bot.place_market_order(self.params["instruments"], -self.ORDER_SIZE)
        # self.bot.place_limit_order(
        #     self.params["instruments"],
        #     -self.ORDER_SIZE,
        #     self.df["resistance"].iloc[-1],
        #     self.df["support"].iloc[-1],
        # )
        # print()

    def handle_take_profit(self):
        print("Price at resistance level, closing position...")
        # stoplossprice = self.bot.get_stop_loss_price(
        #     self.params["instruments"], -self.ORDER_SIZE
        # )
        # takeprofitprice = self.bot.get_take_profit_price(
        #     self.params["instruments"], -self.ORDER_SIZE
        # )
        self.bot.place_limit_order_take_profit(
            self.params["instruments"],
            -self.ORDER_SIZE,
            self.df["resistance"].iloc[-1],
            self.df["support"].iloc[-1],
        )

    def handle_stop_loss(self):
        print("Price at support level, closing position...")
        # stoplossprice = self.bot.get_stop_loss_price(
        #     self.params["instruments"], -self.ORDER_SIZE
        # )
        # takeprofitprice = self.bot.get_take_profit_price(
        #     self.params["instruments"], -self.ORDER_SIZE
        # )
        self.bot.place_limit_order_stop_loss(
            self.params["instruments"],
            -self.ORDER_SIZE,
            self.df["resistance"].iloc[-1],
            self.df["support"].iloc[-1],
        )

    def process_tick(self, tick):
        print("Processing tick...")
        process_streaming_response(tick, self.temp_list)
        print(
            f"Time: {tick['time']}, {colored('closeoutBid:', 'green')} {tick['closeoutBid']}, {colored('closeoutAsk:', 'red')} {tick['closeoutAsk']}"
        )
        print()
        if datetime.now() - self.interval_start >= self.interval:
            print("Aggregating data at 1-minute interval...")
            self.interval_start = datetime.now()
            if self.temp_list:
                new_df = get_candlestick_data(self.interval_start, self.temp_list)
                action = self.qtrader.update(self.df, new_df)
                positions = self.bot.get_open_positions()
                print(f"Open positions: {positions}")
                print()
                instruments_in_positions = [
                    position["instrument"] for position in positions
                ]

                if (
                    action == self.ACTION_BUY
                    and self.params["instruments"] not in instruments_in_positions
                ):
                    self.handle_buy_action()
                elif (
                    action == self.ACTION_SELL
                    and self.params["instruments"] in instruments_in_positions
                ):
                    self.handle_sell_action()
                elif (
                    abs(self.temp_list[-1] - self.df["resistance"].iloc[-1])
                    <= 1 * 10**-self.precision
                    and self.params["instruments"] in instruments_in_positions
                    and self.bot.get_buy_in_price(self.params["instruments"])
                    < self.df["resistance"].iloc[-1]
                ):
                    self.handle_take_profit()
                elif (
                    self.temp_list[-1] <= self.df["support"].iloc[-1]
                    and self.params["instruments"] in instruments_in_positions
                    and self.bot.get_buy_in_price(self.params["instruments"])
                    > self.df["support"].iloc[-1]
                ):
                    self.handle_stop_loss()
                else:
                    print("Holding position...")
                self.df = pd.concat([self.df, new_df], ignore_index=True)
                self.temp_list.clear()
                self.df = calculate_indicators(self.df)
                print(self.df.tail(5))
                print()
        else:
            print("Gathering streaming data...")

    def run(self):
        self.qtrader.train(self.df)
        print()
        r = pricing.PricingStream(accountID=self.accountID, params=self.params)
        try:
            rv = self.client.request(r)
            for tick in rv:
                if self.check_max_duration():
                    self.bot.close_all_trades()
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
