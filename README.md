# QTraderFX

<img src="./pics/qtrader.png" alt="Logo" width="300"/>

<br/>
<br/>

QTraderFX is an algorithmic trading project that implements a Q-learning based trading strategy. It operates and interacts with the forex market using minute-interval data fetched from OANDA's API. This is a work in progress project. Currently it only supports a subset of currency pairs and limited to long positions only.

<br/>

## High Level Workflow Diagram

```mermaid
classDiagram
direction LR
class StreamingPipeline {
    +process_tick()
    +fetch_candlestick_data()
    +handle_buy_action()
    +handle_sell_action()
    +handle_take_profit()
    +handle_stop_loss()
    +perform_action()
}


class QLearningTrader {
    +chooseAction()
    +calculate_reward()
    +take_action()
    +train()
    +update
}

class FetchHistoricalData {
    +fetch_and_process_data()
}

class TradingBot {
    +get_open_positions()
    +get_current_price()
    +get_buy_in_price()
    +get_take_profit_price()
    +get_stop_loss_price()
    +place_market_order()
    +place_limit_order()
    +place_limit_order_take_profit()
    +place_limit_order_stop_loss()
    +close_all_trades()
}



FetchHistoricalData -->  QLearningTrader: Train and backtest
QLearningTrader --> StreamingPipeline: Interacts with to derive signals real time
TradingBot --> StreamingPipeline : Place orders real time

```

## Features
Utilizes Q-learning algorithm for decision-making in trading.
Trades on the forex market with minute-interval data.
Designed for use with OANDA brokerage.


#### References:
https://oanda-api-v20.readthedocs.io  
https://github.com/AminHP/gym-anytrading/tree/master  
https://stable-baselines.readthedocs.io/en/master/modules/a2c.html  
