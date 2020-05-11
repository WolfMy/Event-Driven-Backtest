from queue import Queue
import time, datetime


from data import MySQLDataHandler
from strategy import BuyAndHoldStrategy, DoubleMAStrategy
from portfolio import NaivePortfolio
from execution import SimulatedExecutionHandler
from plot import pyechartsPlotor

events = Queue()
bars = MySQLDataHandler(events, ['BTC-USDT'], '127.0.0.1', 'root', 'Mouyu0407', 'okex')
port = NaivePortfolio(bars, events, datetime.datetime.utcnow(), initial_capital=100000.0)
strategy = DoubleMAStrategy(5, 13, bars, events)
broker = SimulatedExecutionHandler(bars, events)
plotor = pyechartsPlotor(bars, events)

while True:
    # Update the bars (specific backtest code, as opposed to live trading)
    if bars.continue_backtest:
        bars.update_bars()
    else:
        #port.create_equity_curve_dataframe()
        #port.output_summary_stats()
        plotor.update_ma_data(strategy)
        plotor.process_plot_data()
        plotor.plot_kline()
        break

    # Handle the events
    while True:
        try:
            event = events.get(False)
        except Exception as e:
            break
        else:
            if event is not None:
                if event.type == 'MARKET':
                    strategy.calculate_signals(event)
                    port.update_timeindex(event)
                    plotor.update_kline_data(event)

                elif event.type == 'SIGNAL':
                    port.update_signal(event)

                elif event.type == 'ORDER':
                    broker.execute_order(event)

                elif event.type == 'FILL':
                    port.update_fill(event)
                    plotor.update_markpoint(event)
                    
    # 10-Minute heartbeat
    #time.sleep(0.1*60)