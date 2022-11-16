class Strategy(StrategyBase):
    def __init__(self):
        # strategy attributes
        self.period = 24 * 60 * 60
        self.subscribed_books = {}
        self.options = {}

        # define your attributes here
        self.window_size = 5
        self.rsi_history_size = 7
        self.rsi_history = [] # record latest
        self.rsi_lag_history = []
        self.lag = 2
        self.label = -1


    def on_order_state_change(self,  order):
        pass

    def RSI(self, close_price_history, window_size, lag):
        '''calculating the rsi value'''
        # close in closes is from newest to oldest
        rises = []
        falls = []
        for i in range(window_size):
            dif = close_price_history[i] - close_price_history[i+lag]
            if dif > 0:
                rises.append(dif)
            else:
                falls.append(dif)
        rises_avg = sum(rises) / len(rises) if len(rises) > 0 else 0
        falls_avg = sum(falls) / len(falls) if len(falls) > 0 else 0
        return rises_avg / (rises_avg - falls_avg) * 100

    def sell(self, available_base_amount, base, exchange, pair):
        '''sell function'''
        if available_base_amount > 0:
            CA.log('賣出 ' + base)
            CA.sell(exchange, pair, available_base_amount, CA.OrderType.MARKET)
            self.label = 0
        else:
            CA.log('可賣資產不足')

    def buy(self, available_quote_amount, base, exchange, pair, latest_close_price):
        '''buy function'''
        amount = 0.2
        if available_quote_amount >= amount * latest_close_price:
            CA.log('買入 ' + base)
            CA.buy(exchange, pair, amount, CA.OrderType.MARKET)
            self.label = 1
        else:
            CA.log('可買資產不足')

    def trend(self, rsi_history):
        '''
        Calculating the current trend. If return value > 1,
        then indicate the market is in an increasing trend,
        otherwise in decreasing trend.
        '''
        trend_cnt = 0
        for i in range(len(rsi_history)-1):
            if rsi_history[i+1] != 0:
                trend_cnt += rsi_history[i] / rsi_history[i+1]
            else :
                trend_cnt += 1
        return trend_cnt / (len(rsi_history) -1)

    def trade(self, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()

        if len(candles[exchange][pair]) < 2*self.window_size + 1:
            return
        # close_price_history is from newest to oldest
        close_price_history = [candle['close'] for candle in candles[exchange][pair]]
        close_price_history = np.array(close_price_history)

        rsi = self.RSI(close_price_history, self.window_size, 1)
        rsi_lag = self.RSI(close_price_history, self.window_size, self.lag)

        # content in self.rsi_history is from oldest to newest
        self.rsi_history.append(rsi)
        self.rsi_lag_history.append(rsi_lag)
        if len(self.rsi_history) < 3:
            return

        if len(self.rsi_history) > self.rsi_history_size:
            self.rsi_history.pop(0)
            self.rsi_lag_history.pop(0)

        # get available balance
        base_balance = CA.get_balance(exchange, base)
        quote_balance = CA.get_balance(exchange, quote)
        available_base_amount = base_balance.available
        available_quote_amount = quote_balance.available

        trend = self.trend(self.rsi_history)


        if trend <  0.5:
            CA.log("sell by trend : " + str(trend))
            self.sell(available_base_amount, base, exchange, pair)
        elif  self.rsi_lag_history[-1] > 80:
            CA.log("sell by predict reverse : " + str(self.rsi_lag_history[-1]))
            self.sell(available_base_amount, base, exchange, pair)
        elif trend > 1.5:
            CA.log("buy by trend : " + str(trend))
            self.buy(available_quote_amount, base, exchange, pair, close_price_history[0])
        elif  self.rsi_lag_history[-1] < 20:
            CA.log("buy by predict reverse : " + str(self.rsi_lag_history[-1]) + ": " + str(trend))
            self.buy(available_quote_amount, base, exchange, pair, close_price_history[0])
