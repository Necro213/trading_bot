import MetaTrader5 as mt5
import time
import threading
from components.herramientas import Herramientas
import csv

class BotControllerTest:

    def __init__(self):
        if not mt5.initialize():
            print("inicialize failed", mt5.last_error())
        self.settings = Herramientas()
        print("yes")
        self.symbol = "USDCAD"
        self.count = 0
        self.prices = []
        self.price = self.settings.get_actual_price()
        self.min = self.price
        self.max = self.price
        self.active = False
        self.order = -1
        self.closed_operations = []
        self.average_direction = None
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
            "limite_superior": media,
            "limite_inferior": media
        }

    def check_operations(self):
        while True:
            positions = self.settings.get_positions()
            if len(positions) > 0:
                for order in positions:
                    #ticket = order["ticket"]
                    print(order)
                    if order["type"] == 0:
                        type = mt5.ORDER_TYPE_BUY
                    else:
                        type = mt5.ORDER_TYPE_SELL

                    volume = str(order["volume"])
                    cprice = str(order["price"])
                    aprice = str(self.settings.get_actual_price())
                    profit = str(self.settings.calcule_profit(type, "USDCAD", float(volume), float(cprice), float(aprice)))
                    print(profit)
                    if float(profit) > 0.1 and float(volume) == 0.01:
                        print("close positive order")
                        self.settings.close_position(order)
                        order["profit"] = profit
                        self.closed_operations.append(order)
                        self.add_row_to_csv(order)
                    elif float(profit) > 1 and (float(volume) == 0.1 or float(volume) == 0.2):
                        print("close positive super order")
                        self.settings.close_position(order)
                        order["profit"] = profit
                        self.closed_operations.append(order)
                        self.add_row_to_csv(order)
                    elif float(profit) < -4 and (float(volume) == 0.1 or float(volume) == 0.2):
                        print("close negative super order")
                        self.settings.close_position(order)
                        order["profit"] = profit
                        self.closed_operations.append(order)
                        self.add_row_to_csv(order)
                    elif float(profit) < -1 and float(volume) == 0.01:
                        print("close negative order")
                        self.settings.close_position(order)
                        order["profit"] = profit
                        self.closed_operations.append(order)
                        self.add_row_to_csv(order)
                    elif self.active and float(volume) == 0.01 and order["type"] == self.order:
                        print("close negative order")
                        self.settings.close_position(order)
                        order["profit"] = profit
                        self.closed_operations.append(order)
                        self.add_row_to_csv(order)
            time.sleep(0.5)

    def detect_hook(self):
        new_dif = 0
        dif = 0
        change = None
        price = self.settings.get_actual_price()

        max_func = price
        min_func = price
        while True:
            price = self.settings.get_actual_price()
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
                if resta > 0.001:
                    print("super up")
                    self.order = 1
                    self.active = True
            elif change == "down" and not self.active:
                new_dif = max_func - price
                resta = dif - new_dif
                if resta < 0:
                    resta = resta*(-1)
                if resta > 0.001:
                    print("super down")
                    self.order = 0
                    self.active = True

            if self.active:
                if change == "up":
                    limit = max_func - 0.001

                    if price < limit:
                        print("up -> down")
                        self.settings.create_position(mt5.ORDER_TYPE_SELL, 0.1, price)
                        self.active = False
                        min_func = price
                        max_func = price
                        self.max = price
                        self.min = price

                elif change == "down":
                    limit = min_func + 0.001
                    if price > limit:
                        print("down -> up")
                        self.settings.create_position(mt5.ORDER_TYPE_BUY, 0.1, price)
                        self.active = False
                        min_func = price
                        max_func = price
                        self.max = price
                        self.min = price

            time.sleep(0.5)

    def init_thread(self):
        init_simulate = threading.Thread(target=self.settings.simulate_prices_from_data)
        operations = threading.Thread(target=self.check_operations)
        detect_hook = threading.Thread(target=self.detect_hook)
        trading = threading.Thread(target=self.trading_bot)
        init_simulate.start()
        time.sleep(1)
        self.max = self.settings.get_actual_price()
        self.min = self.settings.get_actual_price()
        operations.start()
        detect_hook.start()
        trading.start()

    def trading_bot(self):
        while True:
            self.count += 1
            #print(self.count)
            price = self.settings.get_actual_price()
            average = 0
            #print(price)
            if self.count == 60:
                self.count = 0
                self.max = price
                self.min = price
            local_cross_direction = self.cross_direction
            if len(self.prices) > 20:
                self.prices.pop(0)
                self.prices.append(price)
                self.cross_direction = self.settings.detect_cross_medias_test(self.prices, price)
            else:
                self.prices.append(price)

            if self.cross_direction != local_cross_direction:
                if self.cross_direction == "cross_up":
                    #self.settings.create_position(mt5.ORDER_TYPE_BUY, 0.1, price)
                    print("cross up")
                elif self.cross_direction == "cross_down":
                    #self.settings.create_position(mt5.ORDER_TYPE_SELL, 0.1, price)
                    print("cross down")
            if self.active:
                self.max = price
                self.min = price
                time.sleep(0.5)
                continue

            ten = self.tendencia(self.prices)
            positions = self.settings.get_positions()
            positions_count = 0
            for order in positions:
                #order = item._asdict()
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
                time.sleep(0.5)
                continue
            print(ten)

            if ten == "up" and limits["limite_superior"] > price:
                print("create buy order")
                self.settings.create_position(mt5.ORDER_TYPE_BUY, 0.01, price)
                self.max = price
                self.min = price
            elif ten == "down" and limits["limite_inferior"] < price:
                print("create sell order")

                self.settings.create_position(mt5.ORDER_TYPE_SELL, 0.01, price)
                self.max = price
                self.min = price

            time.sleep(0.5)

    def add_row_to_csv(self, order):
        with open('data.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(order.values())

botc = BotControllerTest()
botc.init_thread()
#botc.check_operations()

#settings = Herramientas()

#settings.simulate_prices_from_data()

"""settings.calcule_profit(
            mt5.ORDER_TYPE_BUY,
            "USDCAD",
            0.02,
            1.33851,
            1.33749
)"""
