import baostock as bs
import pandas as pd
import os

from tools.file_io.make_nd_clean_dirs import make_dirs


class Downloader(object):
    def __init__(self,
                 output_dir,
                 date_start='1990-01-01',
                 date_end='2020-03-23'):
        self._bs = bs
        bs.login()  # login baostock
        self.date_start = date_start
        # self.date_end = datetime.datetime.now().strftime("%Y-%m-%d")
        self.date_end = date_end
        self.output_dir = output_dir
        self.fields = "date,code,open,high,low,close,volume,amount," \
                      "adjustflag,turn,tradestatus,pctChg,peTTM," \
                      "pbMRQ,psTTM,pcfNcfTTM,isST"

    def exit(self):
        bs.logout()

    def get_codes_by_date(self, date):
        print(date)
        stock_rs = bs.query_all_stock(date)
        stock_df = stock_rs.get_data()
        print(stock_df)
        return stock_df

    def run(self):
        stock_df = self.get_codes_by_date(self.date_end)
        for index, row in stock_df.iterrows():
            print(f'processing {row["code"]} {row["code_name"]}')
            df_code = bs.query_history_k_data_plus(row["code"], self.fields,
                                                   start_date=self.date_start,
                                                   end_date=self.date_end).get_data()
            df_code.to_csv(f'{self.output_dir}/{row["code"]}.{row["code_name"]}.csv', index=False)
        self.exit()


if __name__ == '__main__':
    # 获取全部股票的日K线数据
    make_dirs('./data/train')
    downloader = Downloader('./data/train', date_start='1990-01-01', date_end='2019-11-29')
    downloader.run()

    make_dirs('./data/test')
    downloader = Downloader('./data/test', date_start='2019-12-01', date_end='2019-12-31')
    downloader.run()

