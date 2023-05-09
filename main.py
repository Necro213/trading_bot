import MetaTrader5 as mt5
import time
import threading
from components.herramientas import Herramientas


class BotController:

    def __init__(self, min_vol=0.01, max_vol=0.1, profit_min_vol=0.01, profit_max_vol=1, lost_min_vol=1, lost_max_vol=9,
                 symbol="USDCAD", period_trading=60, period_trasher=5):
        if not mt5.initialize():
            print("inicialize failed", mt5.last_error())
        print("yes")
        self.settings = Herramientas(symbol=symbol)
        self.symbol = symbol
        self.count = 0
        self.prices = []
        self.info = mt5.symbol_info(self.symbol)
        self.price = mt5.symbol_info_tick(self.symbol).ask
        self.min = self.price
        self.max = self.price
        self.active = False
        self.order = -1
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.profit_min_vol = profit_min_vol
        self.profit_max_vol = profit_max_vol
        self.period_trading = period_trading
        self.period_trasher = period_trasher
        self.lost_min_vol = lost_min_vol
        self.lost_max_vol = lost_max_vol
        self.cross_direction = None

    def tendencia(self, prices):
        if len(prices) < 5:
            return "not ready"
        uno_ant_prom = prices[-3]
        dos_ant_prom = prices[-2]
        tres_ant_prom = prices[-1]

        if uno_ant_prom < dos_ant_prom and dos_ant_prom < tres_ant_prom:
            return "up"
        elif uno_ant_prom > dos_ant_prom and dos_ant_prom > tres_ant_prom:
            return "down"
        return "variable"

    def generate_limits(self, max, min):
        media = (max + min) / 2
        limite_sup = (media + max) / 2
        limite_inf = (media + min) / 2

        return {
            "limite_superior": limite_sup,
            "limite_inferior": limite_inf
        }

    def check_operations(self):
        while True:
            positions = mt5.positions_get(symbol=self.symbol)
            if len(positions) > 0:
                for item in positions:
                    order = item._asdict()
                    ticket = order["ticket"]
                    profit = order["profit"]
                    volume = order["volume"]
                    type = order["type"]
                    if volume == self.min_vol and (profit > self.profit_min_vol or profit < self.lost_min_vol):
                        print("close min vol order with profit "+str(profit))
                        mt5.Close(ticket=ticket, symbol=self.symbol)
                    elif volume == self.max_vol and (profit > self.profit_max_vol or profit < self.lost_max_vol):
                        print("close max vol order with profit "+str(profit))
                        mt5.Close(ticket=ticket, symbol=self.symbol)
                    elif self.active and volume == self.min_vol and type == self.order:
                        print("close order for hook")
                        mt5.Close(ticket=ticket, symbol=self.symbol)
            time.sleep(self.period_trasher)

    def detect_hook(self):
        new_dif = 0
        dif = 0
        change = None
        price = mt5.symbol_info_tick(self.symbol).ask

        max_func = price
        min_func = price
        while True:
            price = mt5.symbol_info_tick(self.symbol).ask
            if price > max_func:
                max_func = price
                dif = price - min_func
                change = "up"

            if price < min_func:
                min_func = price
                dif = max_func - price
                change = "down"

            if change == "up" and not self.active:
                new_dif = price - min_func
                resta = dif - new_dif
                if resta < 0:
                    resta = resta * (-1)
                if resta > 40:
                    print("super up")
                    self.order = 1
                    self.active = True
            elif change == "down" and not self.active:
                new_dif = max_func - price
                resta = dif - new_dif
                if resta < 0:
                    resta = resta * (-1)
                if resta > 40:
                    print("super down")
                    self.order = 0
                    self.active = True

            if self.active:
                if change == "up":
                    limit = max_func - 15

                    if price < limit:
                        print("up -> down")
                        self.create_order(mt5.ORDER_TYPE_SELL, price, self.max_vol)
                        self.active = False
                        min_func = price
                        max_func = price
                        self.max = price
                        self.min = price

                elif change == "down":
                    limit = min_func + 15
                    if price > limit:
                        print("down -> up")
                        self.create_order(mt5.ORDER_TYPE_BUY, price, self.max_vol)
                        self.active = False
                        min_func = price
                        max_func = price
                        self.max = price
                        self.min = price

            time.sleep(self.period_trading)

    def detect_cross(self):
        while True:
            price = mt5.symbol_info_tick(self.symbol).ask

            local_cross_direction = self.cross_direction
            if self.settings.detect_cross_medias(price) == "no_cross":
                time.sleep(1)
                continue
            self.cross_direction = self.settings.detect_cross_medias(price)
            if local_cross_direction == "cross_up" and self.cross_direction == "cross_down":
                self.cross_direction = None
                print("cross sell order")
                self.create_order(mt5.ORDER_TYPE_SELL, price, self.max_vol)
            elif local_cross_direction == "cross_down" and self.cross_direction == "cross_up":
                self.cross_direction = None
                print("cross buy order")
                self.create_order(mt5.ORDER_TYPE_BUY, price, self.max_vol)
            time.sleep(1)

    def init_thread(self):
        operations = threading.Thread(target=self.check_operations)
        detect_hook = threading.Thread(target=self.detect_hook)
        trading = threading.Thread(target=self.trading_bot)
        operations.start()
        detect_hook.start()
        trading.start()

        time.sleep(10)
        detect_cross = threading.Thread(target=self.detect_cross)
        detect_cross.start()


    def trading_bot(self):
        while True:
            if self.active:
                time.sleep(self.period_trading)
                continue
            self.count += 1
            price = mt5.symbol_info_tick(self.symbol).ask

            if self.count == 60:
                self.count = 0
                #self.max = price
                #self.min = price

            if len(self.prices) > 20:
                self.prices.pop(0)
                self.prices.append(price)
            else:
                self.prices.append(price)

            ten = self.tendencia(self.prices)
            positions = mt5.positions_get(symbol=self.symbol)
            positions_count = 0
            for item in positions:
                order = item._asdict()
                volume = order["volume"]
                if volume == self.min_vol:
                    positions_count = positions_count + 1
            if price > self.max:
                self.max = price

            if price < self.min:
                self.min = price

            limits = self.generate_limits(self.max, self.min)
            if positions_count > 5:
                time.sleep(self.period_trading)
                continue
            open_price = mt5.symbol_info_tick(self.symbol).bid
            if ten == "up" and limits["limite_superior"] > price > open_price:
                print("create buy order")
                self.create_order(mt5.ORDER_TYPE_BUY, price, self.min_vol)
                self.max = price
                self.min = price
            elif ten == "down" and limits["limite_inferior"] < price < open_price:
                print("create sell order")
                self.create_order(mt5.ORDER_TYPE_SELL, price, self.min_vol)
                self.max = price
                self.min = price

            time.sleep(self.period_trading)

    def create_order(self, type, price, volume):
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": type,
            "price": price,
            # "sl": price + 70,
            # "tp": price - 70,
            "deviation": 20,
            # "magic": 234000,
            "comment": "python script open",
            # "type_time": mt5.ORDER_TIME_GTC,
            # "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        mt5.order_send(request)


botc = BotController(
    min_vol=0.01,
    max_vol=0.05,
    profit_min_vol=0.05,
    profit_max_vol=1,
    lost_min_vol=-1,
    lost_max_vol=-2,
    symbol="BTCUSD",
    period_trading=60,
    period_trasher=3
)
botc.init_thread()
# botc.check_operations()

# settings = Herramientas()

# settings.simulate_prices_from_data()
