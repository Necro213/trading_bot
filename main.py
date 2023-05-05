import MetaTrader5 as mt5
import time
import threading


class BotController:

    def __init__(self):
        if not mt5.initialize():
            print("inicialize failed", mt5.last_error())
        print("yes")
        self.symbol = "USDCAD"
        self.count = 0
        self.prices = []
        self.info = mt5.symbol_info(self.symbol)
        self.price = mt5.symbol_info_tick(self.symbol).ask
        self.min = self.price
        self.max = self.price
        self.active = False
        self.order = -1

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
            #print("check_operations")
            positions = mt5.positions_get(symbol=self.symbol)
            if len(positions) > 0:
                for item in positions:
                    order = item._asdict()
                    ticket = order["ticket"]
                    profit = order["profit"]
                    volume = order["volume"]
                    type = order["type"]
                    #print(type)
                    if profit > 0.04 and volume == 0.01:
                        print("close order")
                        mt5.Close(ticket=ticket, symbol=self.symbol)
                    elif profit > 2 and volume == 0.1:
                        print("close order")
                        mt5.Close(ticket=ticket, symbol=self.symbol)
                    elif profit < -10 and volume == 0.1:
                        print("close order")
                        mt5.Close(ticket=ticket, symbol=self.symbol)
                    elif self.active and volume == 0.01 and type == self.order:
                        print("close order")
                        mt5.Close(ticket=ticket, symbol=self.symbol)
            time.sleep(5)

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
                #print(change)

            if price < min_func:
                min_func = price
                dif = max_func - price
                change = "down"
                #print(change)

            if change == "up" and not self.active:
                new_dif = price - min_func
                resta = dif - new_dif
                if resta < 0:
                    resta = resta * (-1)
                if resta > 0.0005:
                    print("super up")
                    self.order = 1
                    self.active = True
            elif change == "down" and not self.active:
                new_dif = max_func - price
                resta = dif - new_dif
                if resta < 0:
                    resta = resta*(-1)
                if resta > 0.0005:
                    print("super down")
                    self.order = 0
                    self.active = True

            if self.active:
                if change == "up":
                    limit = max_func - 0.0005

                    if price < limit:
                        print("up -> down")
                        request = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "symbol": self.symbol,
                            "volume": 0.1,
                            "type": mt5.ORDER_TYPE_SELL,
                            "price": price,
                            # "sl": price - 80,
                            # "tp": price + 80,
                            "deviation": 20,
                            # "magic": 234000,
                            "comment": "python script open",
                            # "type_time": mt5.ORDER_TIME_GTC,
                            # "type_filling": mt5.ORDER_FILLING_RETURN,
                        }
                        result = mt5.order_send(request)
                        self.active = False
                        min_func = price
                        max_func = price
                        self.max = price
                        self.min = price

                elif change == "down":
                    limit = min_func + 0.0005
                    if price > limit:
                        print("down -> up")
                        request = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "symbol": self.symbol,
                            "volume": 0.1,
                            "type": mt5.ORDER_TYPE_BUY,
                            "price": price,
                            # "sl": price - 80,
                            # "tp": price + 80,
                            "deviation": 20,
                            # "magic": 234000,
                            "comment": "python script open",
                            # "type_time": mt5.ORDER_TIME_GTC,
                            # "type_filling": mt5.ORDER_FILLING_RETURN,
                        }
                        result = mt5.order_send(request)
                        self.active = False
                        min_func = price
                        max_func = price
                        self.max = price
                        self.min = price

            time.sleep(1)

    def init_thread(self):
        operations = threading.Thread(target=self.check_operations)
        detect_hook = threading.Thread(target=self.detect_hook)
        trading = threading.Thread(target=self.trading_bot)
        operations.start()
        detect_hook.start()
        trading.start()

    def trading_bot(self):
        while True:
            if self.active:
                time.sleep(30)
                continue
            self.count += 1
            print(self.count)
            info = mt5.symbol_info(self.symbol)
            point = mt5.symbol_info(self.symbol).point
            price = mt5.symbol_info_tick(self.symbol).ask
            if self.count == 60:
                self.count = 0
                self.max = price
                self.min = price
            if len(self.prices) > 10:
                self.prices.pop(0)
            self.prices.append(price)
            ten = self.tendencia(self.prices)
            positions = mt5.positions_get(symbol=self.symbol)
            positions_count = 0
            for item in positions:
                order = item._asdict()
                volume = order["volume"]
                if volume == 0.01:
                    positions_count = positions_count+1;
            if price > self.max:
                self.max = price
                #print("new max price " + str(self.max))

            if price < self.min:
                self.min = price
                #print("new min price " + str(self.min))

            #print(self.max, price, self.min)
            limits = self.generate_limits(self.max, self.min)
            #print(limits["limite_superior"], price, limits["limite_inferior"])
            if positions_count > 5:
                #print("max positions")
                time.sleep(30)
                continue
            print(ten)

            if ten == "up" and limits["limite_superior"] > price:
                print("create buy order")
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": 0.01,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": price,
                    # "sl": price - 80,
                    # "tp": price + 80,
                    "deviation": 20,
                    # "magic": 234000,
                    "comment": "python script open",
                    # "type_time": mt5.ORDER_TIME_GTC,
                    # "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                result = mt5.order_send(request)
                self.max = price
                self.min = price
            elif ten == "down" and limits["limite_inferior"] < price:
                print("create sell order")

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": 0.01,
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": price,
                    # "sl": price + 70,
                    # "tp": price - 70,
                    "deviation": 20,
                    # "magic": 234000,
                    "comment": "python script open",
                    # "type_time": mt5.ORDER_TIME_GTC,
                    # "type_filling": mt5.ORDER_FILLING_RETURN,
                }

                result = mt5.order_send(request)
                self.max = price
                self.min = price

            time.sleep(30)


botc = BotController()
botc.init_thread()
#botc.check_operations()