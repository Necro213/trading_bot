import MetaTrader5 as mt5
import time


class Herramientas:
    def __init__(self, symbol="USDCAD"):
        mt5.initialize()
        self.symbol = symbol
        self.data = None
        self.actual_price = None
        self.posotions = []

    def get_data(self, limit=1000):
        self.data = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, limit)
        return self.data

    def simulate_prices_from_data(self):
        self.get_data(600)
        prices = []
        for item in self.data:
            self.actual_price = item[4]

            if len(prices) == 20:
                prices.pop(0)
            prices.append(self.actual_price)

            if len(prices) == 20:
                self.adaptative_moving_average_temp(prices)
            time.sleep(0.5)
        print("-----------------------------end---------------------------------")

    def get_actual_price(self):
        return self.actual_price

    def adaptative_moving_average(self, limit=20):
        data = self.get_data(limit)
        prices = []
        for item in data:
            price = item[4]
            prices.append(price)

        prices.append(mt5.symbol_info_tick(self.symbol).ask)
        prices.reverse()
        ema = 0
        for item in prices:
            ema = ema + item
        ema = ema / len(prices)

        # print(ema)
        return ema

    def adaptative_moving_average_temp(self, prices):
        ema = 0
        for item in prices:
            ema = ema + item
        ema = ema / len(prices)
        return ema

    def calcule_profit(self, order_type, symbol, volume, price_open, price_close):
        profit = mt5.order_calc_profit(order_type, symbol, volume, price_open, price_close)
        return profit

    def get_positions(self):
        return self.posotions

    def create_position(self, type, volume, price):
        self.posotions.append({
            "price": price,
            "type": type,
            "volume": volume
        })

    def close_position(self, position):
        for i in range(len(self.posotions)):
            if self.posotions[i]['price'] == position["price"]:
                del self.posotions[i]
                break

    def detect_cross_medias_test(self, prices_35, price):
        ema_35 = self.adaptative_moving_average_temp(prices_35)

        if price > ema_35 + 0.0002:
            return "cross_up"
        elif price < ema_35 - 0.0002:
            return "cross_down"

    def detect_cross_medias(self, price):
        ema_20 = self.adaptative_moving_average(19)

        if price > ema_20 + 10:
            return "cross_up"
        elif price < ema_20 - 10:
            return "cross_down"
        return "no_cross"

    def can_buy(self):
        price = mt5.symbol_info_tick(self.symbol).ask
        price_open = mt5.symbol_info_tick(self.symbol).bid

        last_tick = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, 1)
        last_tick_open = last_tick[0][1]
        last_tick_close = last_tick[0][4]

        if (last_tick_close > last_tick_open) and (price > price_open):
            return True
        return False

    def can_sell(self):
        price = mt5.symbol_info_tick(self.symbol).ask
        price_open = mt5.symbol_info_tick(self.symbol).bid

        last_tick = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, 1)
        last_tick_open = last_tick[0][1]
        last_tick_close = last_tick[0][4]

        if (last_tick_close < last_tick_open) and (price < price_open):
            return True
        return False
