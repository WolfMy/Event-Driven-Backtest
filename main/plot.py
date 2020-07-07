import datetime
import pandas as pd
import numpy as np
from pyecharts.charts import Kline, Line
from pyecharts import options as opts

from event import FillEvent

class pyechartsPlotor(object):
    """
    绘图类负责收集bars数据以及fill买卖点，在回测完成时，绘制出K线图。
    """
    def __init__(self, bars, events):
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list

        self.x_axis = {}
        self.data = {}
        self.ma1_data = {}
        self.ma2_data = {}
        self.markpoint = {}
        self.markline = {}

        # Set the x_axis, data, markpoint to None
        for s in self.symbol_list:
            self.x_axis[s] = []
            self.data[s] = []
            self.ma1_data[s] = []
            self.ma2_data[s] = []
            self.markpoint[s] = []
            self.markline[s] = []

    def update_kline_data(self, event):
        bars = {}
        for sym in self.symbol_list:
            bars[sym] = self.bars.get_latest_bars(sym, N=1)

        # Update x_axis and data
        for s in self.symbol_list:
            x_axis = bars[s][0][1].strftime('%m-%d %H:%M')
            self.x_axis[s].append(x_axis)

            # Data [open, close, low, high]
            data = [bars[s][0][2], bars[s][0][5], bars[s][0][4], bars[s][0][3]]
            self.data[s].append(data)

    def update_markpoint(self, event):
        # Markpoint [datetime, fill_cost, quantity, direction]
        self.markpoint[event.symbol].append([event.timeindex, event.fill_cost, event.quantity, event.direction])
    
    def update_ma_data(self, strategy):
        for s in self.symbol_list:
            self.ma1_data[s] = strategy.ma_data[s]['MA_'+str(strategy.ma1_timeperiod)].values.tolist()
            self.ma2_data[s] = strategy.ma_data[s]['MA_'+str(strategy.ma2_timeperiod)].values.tolist()

    def process_plot_data(self):
        for s in self.symbol_list:
            # Drop duplicates for x_axis and data
            self.x_axis[s] = pd.DataFrame(self.x_axis[s])
            self.data[s] = pd.DataFrame(self.data[s])
            x_axis_unique = ~self.x_axis[s].duplicated(keep='last')
            self.data[s] = self.data[s][x_axis_unique]
            self.x_axis[s] = self.x_axis[s].drop_duplicates(keep='last')

            # Transform x_axis and data to list
            self.x_axis[s] = self.x_axis[s][0].values.tolist()
            self.data[s] = self.data[s].values.tolist()
            
            # Transform markpoint to MarkPointItem_list
            markpoint = [opts.MarkPointItem(
                                    coord=[point[0].strftime('%m-%d %H:%M'), point[1]],
                                    value=point[3]+'\n'+str(point[1]),
                                    symbol='pin' if point[3]=='SELL' else 'pin',
                                    #symbol_size=30
                                    itemstyle_opts=opts.ItemStyleOpts(
                                        color='#911146' if point[3]=='BUY' else '#1F8A70'
                                        )
                                    ) for point in self.markpoint[s]]
            
            # Generate markline based on markpoint
            self.markline[s] = [opts.MarkLineItem(
                                    y=point[1],
                                    name='SHORT' if point[3]=='SELL' else 'LONG'
                                    ) for point in self.markpoint[s]]

            self.markpoint[s] = markpoint

    def plot_kline(self):
        for sym in self.symbol_list:
            kline = (
                Kline()
                .add_xaxis(self.x_axis[sym])
                .add_yaxis(
                    series_name='candle60s '+sym, 
                    y_axis=self.data[sym], 
                )
                .set_series_opts(
                    markpoint_opts=opts.MarkPointOpts(
                        data=self.markpoint[sym],
                        label_opts=opts.LabelOpts(
                            position='inside',
                            color='#ECF0F1',
                            font_size=8
                        )
                    ),
                    #markline_opts=opts.MarkLineOpts(
                    #    data=self.markline[sym]
                    #)
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="回测结果", pos_left="0"),
                    xaxis_opts=opts.AxisOpts(
                        type_="category",
                        is_scale=True,
                        boundary_gap=False,
                    ),
                    yaxis_opts=opts.AxisOpts(
                        is_scale=True,
                        #splitline_opts=opts.SplitLineOpts(
                        #    is_show=True, linestyle_opts=opts.LineStyleOpts(width=1)
                        #),
                        splitarea_opts=opts.SplitAreaOpts(
                            is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                        ),
                    ),
                    datazoom_opts=[opts.DataZoomOpts(type_="slider",range_start=0,range_end=20)],
                )
            )
            line = (
                Line()
                .add_xaxis(self.x_axis[sym])
                .add_yaxis(
                    series_name="MA5",
                    y_axis=self.ma1_data[sym],
                    is_smooth=True,
                    is_hover_animation=False,
                    linestyle_opts=opts.LineStyleOpts(width=3, opacity=0.5),
                    label_opts=opts.LabelOpts(is_show=False),
                )
                .add_yaxis(
                    series_name="MA13",
                    y_axis=self.ma2_data[sym],
                    is_smooth=True,
                    is_hover_animation=False,
                    linestyle_opts=opts.LineStyleOpts(width=3, opacity=0.5),
                    label_opts=opts.LabelOpts(is_show=False),
                )
                .set_global_opts(
                    xaxis_opts=opts.AxisOpts(type_="category"),
                    yaxis_opts=opts.AxisOpts(is_scale=True)
                )
            )
            overlap_kline_line = kline.overlap(line)
            overlap_kline_line.render('../result/%s.html' % sym)