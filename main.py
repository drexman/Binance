import logging
import pandas as pd
import time
from datetime import datetime
import matplotlib.pyplot as plt
import finplot as fplt
import plotly.graph_objects as go
from binance.client import Client


API_KEY = "9zYkrYSYgwjhq7oPgRzlBxwz0Cz4enxJZQOd5PFDaZqDo8MpGu9ePQg1kBlB4Seq"
secret_key = "0brVR1licvfl20SiR49g95GZNjzuHJwz5Q4u1XvmG4747gVw8npPyB4gHNivQ4UH"

condle_period_15minutes = Client.KLINE_INTERVAL_15MINUTE

logging.basicConfig(
    filename="src/logs/trading_bot.log",
    format='%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
)

class BinanceTrader():

    last_trader_decision : bool

    def __init__ (self, stock_code, operation_code, trader_quantity, trader_percentage, candle_period):
        self.stock_code = stock_code; # Código parcial da stock negociada (ex : 'BTC')
        self.operation_code = operation_code # Código negociado moeda (ex : 'BTCBRL')
        self.trader_quantity =  trader_quantity    
        self.trader_percentage = trader_percentage
        self.candle_period = candle_period

        self.cliente_binance = Client(API_KEY, secret_key) # Inicia o cliente da Binance

        #self.updateAllData()
        self.updateCloseOpenTime()
        print('Robo iniciando...')

    def updateAllData(self):
        self.account_data = self.getAccount()
        self.last_stock_account_balance = self.getLastStockAccountBalance()
        self.actual_trader_position = self.getActualTradePosition()
        self.stock_data = self.getStockData_ClosePrice_OpenTime()

    def updateCloseOpenTime(self):
        self.getStockDataDay_ClosePrice_OpenTime();

    def getLastStockAccountBalance(self):
        in_wallet_amout = 0
        for stock in self.account_data['balances']:
            if stock['asset'] == self.stock_code:
                in_wallet_amout= stock['free']
        return float(in_wallet_amout)        

    def getActualTradePosition(self):
        return self.last_stock_account_balance > 0.001
    
    def getStockDataDay_ClosePrice_OpenTime(self) :
        candles = self.cliente_binance.get_klines(symbol=self.operation_code, interval=self.candle_period, limit=100) 

        indexes = ['Open Time', 'Open', 'High','Low', 'Close', 'Volume', 'Close Time', 'QAV', 'No. Trades', 'Taker BBAV', 'Taker BQAV', 'Ignore']
        data = pd.DataFrame(columns=indexes,data=candles)
        # Transforma um DataFrame Pandas

        data["Open Time"] = pd.to_datetime(data["Open Time"], unit = "ms").dt.tz_localize("UTC")
        data["Open Time"] = data["Open Time"].dt.tz_convert("America/Sao_Paulo")

        #data["Close Time"] = pd.to_datetime(data["Close Time"], unit = "ms").dt.tz_localize("UTC")
        #data["Close Time"] = data["Close Time"].dt.tz_convert("America/Sao_Paulo")

        data['Open'] = pd.to_numeric(data['Open'])
        data['High'] = pd.to_numeric(data['High'])
        data['Low'] = pd.to_numeric(data['Low'])
        data['Close'] = pd.to_numeric(data['Close'])

        print(data[['Open', 'High', 'Low', 'Close']].values)

        fig = go.Figure(data=[go.Candlestick(x=data['Open Time'], open=data['Open'],high=data['High'],low=data['Low'], close=data['Close'])])
        fig.show()

     

    def getStockData_ClosePrice_OpenTime(self):
        candles = self.cliente_binance.get_klines(symbol = self.operation_code, interval = self.candle_period, limit = 100)

        indexes = ['Open Time', 'Open', 'High','Low', 'Close', 'Volume', 'Close Time', 'QAV', 'No. Trades', 'Taker BBAV', 'Taker BQAV', 'Ignore']
        data = pd.DataFrame(columns=indexes,data=candles)
        # Transforma um DataFrame Pandas
        data["Open Time"] = pd.to_datetime(data["open_time"], unit = "ms").dt.tz_localize("UTC")
        data["Open Time"] = data["open_time"].dt.tz_convert("America/Sao_Paulo")

        return data

    def getMovingAverageTraderStrategy(self, fast_window = 7, slow_window = 40):

        #Calcular as médias moveis rápida e lenta
        self.stock_data['ma_fast'] = self.stock_data["close_price"].rolling(window=fast_window).mean() # Média rápido
        self.stock_data['ma_show'] = self.stock_data["close_price"].rolling(window=slow_window).mean() # Média lenta


        last_ma_fast = self.stock_data["ma_fast"].iloc[-1]
        last_ma_slow = self.stock_data["ma_slow"].iloc[-1]


        if last_ma_fast > last_ma_slow:
            self.ma_trader_decision = True    
        else:
            self.ma_trader_decision= False

        print('_____')
        print('Estratégia executada: Moving Average')
        print(f'({self.operation_code})\n | {last_ma_fast:.3f} = última média rapido\n | {last_ma_slow:.3f}')

    def getAccount(self):
        return self.cliente_binance.get_account()
    

    def get_current_price(self):
        ticker = self.cliente_binance.get_symbol_ticker(symbol=self.operation_code)
        return float(ticker['price'])

    def place_buy_order(self):
        order = self.cliente_binance.order_market_buy(symbol=self.operation_code, quantity = self.trader_quantity)
        print(f'Ordem de compra executado {order}')
    def place_seller_order(self):
        order = self.cliente_binance.order_market_sell(symbol=self.operation_code, quantity = self.trader_quantity)
        print(f'Ordem de venda executado {order}')

    def execute(self):
        self.updateCloseOpenTime()
        
traderBot =  BinanceTrader('BTC','BTCUSDT', 0.001, 100, condle_period_15minutes) 

while True:
    traderBot.execute()
    time.sleep(15)