class Strategy(StrategyBase):
    '''黃金交叉與死亡交叉'''
    def __init__(self):
        # strategy attributes
        self.period = 24 * 60 * 60
        self.subscribed_books = {}
        self.options = {}

        # define your attributes here
        self.short_window_size = 5
        self.long_window_size = 10
        self.rsi_history_size = 7
        self.short_rsi_history = [] # record latest 5 rsi
        self.long_rsi_history = [] # record latest 5 rsi
        self.lag = 3


    def on_order_state_change(self,  order):
        pass
    def RSI(self, closes, window_size, lag):
        # close in closes is from newest to oldest
        rises = []
        falls = []
        for i in range(window_size):
            dif = closes[i] - closes[i+lag]
            if dif > 0:
                rises.append(dif)
            else:
                falls.append(dif)
        rises_avg = sum(rises) / len(rises) if len(rises) > 0 else 0
        falls_avg = sum(falls) / len(falls) if len(falls) > 0 else 0
        return rises_avg / (rises_avg - falls_avg) * 100

    def trade(self, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()

        # get the latest 10 candles
        if len(candles[exchange][pair]) < self.long_window_size + self.lag + 1:
            return
        candles[exchange][pair] = candles[exchange][pair][:2 * self.long_window_size]
        # use close price
        close_price_history = [candle['close'] for candle in candles[exchange][pair]]

        # convert to chronological order for talib
        # After reverse, close_price_history is from oldest to newest.
        # convert np.array

        close_price_history = np.array(close_price_history)
        long_rsi = self.RSI(close_price_history, self.long_window_size, self.lag)
        short_rsi = self.RSI(close_price_history, self.short_window_size, self.lag)
        # CA.log(long_rsi)
        self.long_rsi_history.append(long_rsi)
        self.short_rsi_history.append(short_rsi)
        if len(self.short_rsi_history) > self.rsi_history_size:
            self.short_rsi_history.pop(0)
            self.long_rsi_history.pop(0)

        # get available balance
        base_balance = CA.get_balance(exchange, base)
        quote_balance = CA.get_balance(exchange, quote)
        available_base_amount = base_balance.available
        available_quote_amount = quote_balance.available
        if len(self.short_rsi_history) < 2:
            return
        if self.short_rsi_history[-2] < self.long_rsi_history[-2] and self.short_rsi_history[-1] >= self.long_rsi_history[-1]:
            CA.log('黃金交叉')
            amount = 0.1
            if available_quote_amount >= amount * close_price_history[-1]:
                CA.log('買入 ' + base)
                CA.buy(exchange, pair, amount, CA.OrderType.MARKET)
            else:
                CA.log('資產不足')
        elif self.short_rsi_history[-2] > self.long_rsi_history[-2] and self.short_rsi_history[-1] <= self.long_rsi_history[-1]:
            CA.log('死亡交叉')
            if available_base_amount > 0:
                CA.log('賣出 ' + base)
                CA.sell(exchange, pair, available_base_amount, CA.OrderType.MARKET)
            else:
                CA.log('資產不足')
