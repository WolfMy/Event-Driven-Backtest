import datetime
import pandas as pd
import pymysql

from abc import ABCMeta, abstractmethod

from event import MarketEvent

class DataHandler(object):
    """
    DataHandler is an abstract base class providing an interface for
    all subsequent (inherited) data handlers (both live and historic).

    The goal of a (derived) DataHandler object is to output a generated
    set of bars (OLHCVI) for each symbol requested. 

    This will replicate how a live strategy would function as current
    market data would be sent "down the pipe". Thus a historic and live
    system will be treated identically by the rest of the backtesting suite.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_symbol list,
        or fewer if less bars are available.
        """
        raise NotImplementedError("Should implement get_latest_bars()")

    @abstractmethod
    def update_bars(self):
        """
        Pushes the latest bar to the latest symbol structure
        for all symbols in the symbol list.
        """
        raise NotImplementedError("Should implement update_bars()")

class MySQLDataHandler(DataHandler):
    """
    MySQLDataHandler is designed to read data from Mysql and provide an interface
    to obtain the "latest" bar in a manner identical to a live
    trading interface. 
    """
    def __init__(self, events, symbol_list, host, user, passwd, db):
        """
        Initialises the Mysql data handler by connecing
        MySQL database.

        Parameters:
        events - The Event Queue.
        host - Mysql host.
        user - Mysql username.
        passwd - Mysql password.
        db - Mysql databse.
        """
        self.events = events
        # connect Mysql database
        mysql = pymysql.connect(host, user, passwd, db)
        self.cursor = mysql.cursor()
        self.symbol_list = symbol_list
        
        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True 

        self._query_convert_data()
    
    def _query_convert_data(self):
        """
        Querys the data from Mysql, converting them into 
        pandas DataFrames within a symbol dictionary.
        """
        comb_index = None
        sql = "SELECT * FROM CANDLE60S"
        try:
            self.cursor.execute(sql)
            res = self.cursor.fetchall()
            #res = self.cursor.fetchmany(1000)
        except Exception as e:
            print(e)

        symbol_data = pd.DataFrame(res, columns=['id','timestamp', 'open', 'high', 'low', 'close', 'volume', 'instrument_id'])
        symbol_data.set_index('timestamp', inplace=True)
        symbol_data.drop(['id'], axis=1, inplace=True)

        for s in self.symbol_list:
            self.symbol_data[s] = symbol_data[symbol_data['instrument_id']==s]

            # Combine the index to pad forward values
            if comb_index is None:
                comb_index = self.symbol_data[s].index
            else:
                comb_index.union(self.symbol_data[s].index)
            # Set the latest symbol_data to None
            self.latest_symbol_data[s] = []
        
        # Reindex the dataframes
        for s in self.symbol_list:
            self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad').iterrows()

    def _get_new_bar(self, symbol):
        """
        Returns the latest bar from the data feed as a tuple of 
        (sybmbol, datetime, open, low, high, close, volume).
        """
        for b in self.symbol_data[symbol]:
            yield tuple([symbol, datetime.datetime.strptime(b[0], '%Y-%m-%dT%H:%M:%S.%fZ'), 
                        b[1][0], b[1][1], b[1][2], b[1][3], b[1][4]])
    
    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_symbol list,
        or N-k if less available.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
        else:
            return bars_list[-N:]

    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """
        for s in self.symbol_list:
            try:
                bar = next(self._get_new_bar(s))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[s].append(bar)
        self.events.put(MarketEvent())