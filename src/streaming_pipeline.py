from datetime import datetime, timedelta
from typing import Dict, List

import oandapyV20
import oandapyV20.endpoints.pricing as pricing
import pandas as pd
from loguru import logger
from termcolor import colored

from src.q_learning import QLearningTrader
from src.trading_bot import TradingBot
from src.utils import (
    calculate_indicators,
    get_candlestick_data,
    process_streaming_response,
)


class StreamingDataPipeline:
    ACTION_BUY = 0
    ACTION_SELL = 1
    ACTION_HOLD = 2
    ORDER_SIZE = 100000  # 100,000 units of the base currency

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

    def check_max_duration(self) -> bool:
        """
        Check if the maximum duration has been reached. We are adpopting
        a time-based approach to stop the streaming pipeline.

        Returns:
            bool: True if the maximum duration has been reached
        """
        if datetime.now() - self.start_time >= self.max_duration:
            print("Maximum duration reached, exiting...")
            return True
        return False

    def handle_buy_action(self) -> None:
        """Execute the buy action and print the message to the
        console."""
        print("\nNo open position and Agent recommends buying...\n")
        print("Placing market order to buy...\n")
        self.bot.place_market_order(self.params["instruments"], self.ORDER_SIZE)

    def handle_sell_action(self) -> None:
        """Execute the sell action and print the message to the
        console."""
        print("\nAction is 1 and there are open positions...\n")
        print("Placing limit order to sell...\n")
        self.bot.place_market_order(self.params["instruments"], -self.ORDER_SIZE)

    def handle_take_profit(self) -> None:
        """Execute the take profit action when the price is at the
        resistance level and print the message to the console."""
        print(colored("\nPrice at resistance level, closing position...\n", "yellow"))
        self.bot.place_limit_order_take_profit(
            self.params["instruments"],
            -self.ORDER_SIZE,
            self.df["resistance"].iloc[-1],
            self.df["support"].iloc[-1],
        )

    def handle_stop_loss(self) -> None:
        """Execute the stop loss action when the price is at the
        resistance level and print the message to the console."""
        print(colored("\nPrice at support level, closing position...\n", "red"))
        self.bot.place_limit_order_stop_loss(
            self.params["instruments"],
            -self.ORDER_SIZE,
            self.df["resistance"].iloc[-1],
            self.df["support"].iloc[-1],
        )

    def perform_action(self, action: int, instruments_in_positions: List) -> None:
        """
        Perform the action based on the agent's recommendation and the
        current state of the positions.

        Args:
            action (int): action recommended by the agent
            instruments_in_positions (List): list of instruments in open positions
        """
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

    def process_tick(self, tick: Dict) -> None:
        """
        Process the tick data and update the dataframe.

        Args:
            tick (Dict): tick data from the API
        """
        process_streaming_response(tick, self.temp_list)
        print(
            f"\nTime: {tick['time']},"
            f"{colored('closeoutBid:', 'green')} {tick['closeoutBid']},"
            f"{colored('closeoutAsk:', 'red')} {tick['closeoutAsk']}\n\n"
        )
        if datetime.now() - self.interval_start >= self.interval:
            print("Aggregating data at the minute-interval...")
            self.interval_start = datetime.now()
            if self.temp_list:
                new_df = get_candlestick_data(self.interval_start, self.temp_list)
                action = self.qtrader.update(self.df, new_df)
                positions = self.bot.get_open_positions()
                print(f"Open positions: {positions}\n\n")
                instruments_in_positions = [
                    position["instrument"] for position in positions
                ]

                self.perform_action(action, instruments_in_positions)

                self.df = pd.concat([self.df, new_df], ignore_index=True)
                self.temp_list.clear()
                self.df = calculate_indicators(self.df)
                logger.info(f"Latest incoming data: {self.df.tail(1)}\n\n")
        else:
            print("Gathering streaming data...\n\n")

    def run(self) -> pd.DataFrame:
        """
        Run the streaming pipeline.

        Returns:
            pd.DataFrame: dataframe containing the
            the data during the streaming process
        """
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
                except Exception:
                    print(
                        colored(
                            "Processing heartbeat messages for network latency check",
                            "blue\n\n",
                        )
                    )
        except oandapyV20.exceptions.V20Error as err:
            print(f"V20Error encountered: {err}")
        except KeyboardInterrupt:
            print("Streaming stopped by user.")
        finally:
            return self.df
