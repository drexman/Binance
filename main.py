import logging
import pandas as pd
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import mplfinance as mpf
from lightweight_charts import Chart
from binance.client import Client


API_KEY = "9zYkrYSYgwjhq7oPgRzlBxwz0Cz4enxJZQOd5PFDaZqDo8MpGu9ePQg1kBlB4Seq"
secret_key = "0brVR1licvfl20SiR49g95GZNjzuHJwz5Q4u1XvmG4747gVw8npPyB4gHNivQ4UH"

condle_period_15minutes = Client.KLINE_INTERVAL_15MINUTE

logging.basicConfig(
    filename="src/logs/trading_bot.log",
    format='%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
)

FATOR_VOLATILITY = 0.3
ACCEPTABLE_LOSS_PERCENTAGE = 0
STOP_LOSS_PERCENTAGE = 3
FALLBACK_ACTIVATED  = True

DELAY_ENTRE_ORDENS = 15 * 60


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
        #self.updateCloseOpenTime()
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
    
    def getStockDataDay_ClosePrice_OpenTime(self, limit) :
        
        candles = self.cliente_binance.get_klines(symbol=self.operation_code, interval=self.candle_period, limit=limit) 

        indexes = ['date', 'open', 'high','low', 'close', 'volume', 'close date', 'qav', 'No. Trades', 'Taker BBAV', 'Taker BQAV', 'Ignore']
        data = pd.DataFrame(columns=indexes,data=candles)
        # Transforma um DataFrame Pandas

        data['volatility'] = data['close'].rolling(window=40).std()


        # Calculate the 12 period EMA
        data["EMA12"] = data["close"].ewm(span=12, adjust=False).mean()
        # Calculate the 26-period EMA
        data['EMA26'] = data['close'].ewm(span=26, adjust=False).mean()

        last_mv_fast = data["EMA12"].iloc[-1]
        prev_mv_fast = data["EMA12"].iloc[-3]

        last_mv_slow = data["EMA26"].iloc[-1]
        prev_mv_slow = data["EMA26"].iloc[-3]

        fast_gradient = last_mv_fast - prev_mv_fast
        slow_gradient = last_mv_slow - prev_mv_slow

        current_diff = abs(last_mv_fast - last_mv_slow)

        ma_trade_decision = None 

        # Calculate MACD (the difference between 12-period EMA and 26-period EMA)
        data['MACD'] = data['EMA12'] - data['EMA26']

        # Calculate the 9-period EMA of MACD (Signal Line)
        data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['Histogram'] = data['MACD'] -  data['Signal_Line']

        data["date"] = pd.to_datetime(data["date"], unit = "ms")

        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, axis=1)
       
        return data

    def getCalculoMedia(self, data):

        # Calculate the 12 period EMA
        data["EMA12"] = data["close"].ewm(span=12, adjust=False).mean()
        # Calculate the 26-period EMA
        data['EMA26'] = data['close'].ewm(span=26, adjust=False).mean()

        last_mv_fast = data["EMA12"].iloc[-1]
        prev_mv_fast = data["EMA12"].iloc[-3]

        last_mv_slow = data["EMA26"].iloc[-1]
        prev_mv_slow = data["EMA26"].iloc[-3]

        last_volatility = data['volatility'].iloc[-2]

        fast_gradient = last_mv_fast - prev_mv_fast
        slow_gradient = last_mv_slow - prev_mv_slow

        current_diff = abs(last_mv_fast - last_mv_slow)

        ma_trade_decision = None 

        if current_diff < last_volatility * FATOR_VOLATILITY:

            if fast_gradient > 0 and fast_gradient > slow_gradient:
                ma_trade_decision = True
            elif fast_gradient < 0 and fast_gradient < slow_gradient:
                ma_trade_decision = False
                

        return ''
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

    def generate_new_candlestick(self):
        candles = self.cliente_binance.get_klines(symbol=self.operation_code, interval=self.candle_period, limit=1)
        indexes = ['time', 'open', 'high','low', 'close', 'volume', 'close date', 'QAV', 'No. Trades', 'Taker BBAV', 'Taker BQAV', 'Ignore']
        data = pd.DataFrame(columns=indexes,data=candles)

        # Transforma um DataFrame Pandas
        data["time"] = pd.to_datetime(data["time"], unit = "ms")
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, axis=1)
        
        return data.set_index('date', inplace=True)

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


def calculate_sma(df, period: int = 50):
    return pd.DataFrame({
        'time': df['date'],
        f'SMA {period}': df['close'].rolling(window=period).mean()
    }).dropna()

if __name__ == '__main__':
    traderBot =  BinanceTrader('BTC','BTCUSDT', 0.001, 100, condle_period_15minutes) 
    data = traderBot.getStockDataDay_ClosePrice_OpenTime(100)
    chart = Chart(toolbox=True)
    chart.grid(vert_enabled = True, horz_enabled = True)
    chart.topbar.textbox('symbol', 'BTC')

    chart.legend(visible = True, font_family = 'Trebuchet MS', ohlc = True, percent = True)
    chart.fit()
    chart.set(data)
    signal_line = chart.create_line(color = '#ffeb3b')
    sl = pd.DataFrame(columns = ['time','value'])
    sl.time = data['date']
    sl.value = data['EMA12']
    signal_line.set(sl)

    macd_line = chart.create_line(color = '#088F8F')
    macd = pd.DataFrame(columns = ['time','value'])
    macd.time = data['date']
    macd.value = data['EMA26']
    macd_line.set(macd)

    chart.show()

    try:
        while True:
            newCandle = traderBot.getStockDataDay_ClosePrice_OpenTime(1)
            for index, series in newCandle.iterrows():
                chart.update(series)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('interrupted')