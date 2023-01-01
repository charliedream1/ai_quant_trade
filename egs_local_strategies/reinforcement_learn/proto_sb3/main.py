# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/12/26 23:19
# @File     : main_bkp1.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pickle
import pandas as pd
import matplotlib.pyplot as plt

from stable_baselines3.ppo.policies import MlpPolicy
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3 import PPO

from quant_brain.rl.envs.StockTradingEnv0 import StockTradingEnv
from quant_brain.data_io.baostock.get_stock_data import Downloader

from tools.file_io.make_nd_clean_dirs import make_dirs
from tools.file_io.find_files import find_file
from tools.log.log_util import log


class ProtoRLSb3:
    def __init__(self, init_account_balance):
        self.init_account_balance = init_account_balance
        self._model = None

    def train(self, stock_file):
        log.info('Start Training ...')
        df = pd.read_csv(stock_file)
        df = df.sort_values('date')

        # The algorithms require a vectorized environment to run
        env = DummyVecEnv([lambda: StockTradingEnv(df, self.init_account_balance)])

        self._model = PPO(MlpPolicy, env, verbose=0, tensorboard_log='./log')
        self._model.learn(total_timesteps=int(1e4))

    def test(self, stock_file):
        day_profits = []

        df = pd.read_csv(stock_file)
        df = df.sort_values('date')

        env = DummyVecEnv([lambda: StockTradingEnv(df, self.init_account_balance)])
        obs = env.reset()
        for i in range(len(df) - 1):
            action, _states = self._model.predict(obs)
            obs, rewards, done, info = env.step(action)
            profit = env.render()
            day_profits.append(profit)
            if done:
                break
        return day_profits


def get_data(p_dir: str, train_time_lst: list, test_time_lst: list, skip_prep: bool):
    # 获取全部股票的日K线数据
    # 1. get train data
    train_path = os.path.join(p_dir, 'train_' +
                              train_time_lst[0].replace('-', '') + '_' +
                              train_time_lst[1].replace('-', ''))
    if not skip_prep:
        make_dirs(train_path)
        downloader = Downloader(train_path,
                                date_start=train_time_lst[0], date_end=train_time_lst[1])
        downloader.run()

    # 2. get test data
    test_path = os.path.join(p_dir, 'test_' +
                             test_time_lst[0].replace('-', '') + '_' +
                             test_time_lst[1].replace('-', ''))
    if not skip_prep:
        make_dirs(test_path)
        downloader = Downloader(test_path, date_start=test_time_lst[0], date_end=test_time_lst[1])
        downloader.run()

    return train_path, test_path


# ====================================================================================
#                              Main Process
# ====================================================================================
def test_a_stock_trade(train_path, test_path, stock_code, init_account_balance, out_path):
    mdl = ProtoRLSb3(init_account_balance)

    # 1. train
    stock_file = find_file(train_path, str(stock_code))
    mdl.train(stock_file)

    # 2. test
    stock_file = find_file(test_path, str(stock_code))
    daily_profits = mdl.test(stock_file)

    # make plot
    fig, ax = plt.subplots()
    ax.plot(daily_profits, '-o', label=stock_code, marker='o', ms=10, alpha=0.7, mfc='orange')
    ax.grid()
    plt.xlabel('step')
    plt.ylabel('profit')
    ax.legend()
    out_file = os.path.join(out_path, f'{stock_code}.png')
    plt.savefig(out_file)


def multi_stock_trade(train_path, test_path, test_num=-1, init_account_balance=10000, out_path=''):
    start_code = 600000
    max_num = 3000

    group_result = []

    mdl = ProtoRLSb3(init_account_balance)
    cnt = 0

    for code in range(start_code, start_code + max_num):
        if cnt >= test_num:
            break

        try:
            # 1. train
            stock_file = find_file(train_path, str(code))
            if stock_file is None:
                continue
            mdl.train(stock_file)

            # 2. test
            stock_file = find_file(test_path, str(code))
            if stock_file is None:
                continue
            profits = mdl.test(stock_file)

            group_result.append(profits)
        except Exception as err:
            print(err)

        cnt += 1

    out_file = os.path.join(out_path, f'code-{start_code}-{start_code + max_num}.pkl')
    with open(out_file, 'wb') as f:
        pickle.dump(group_result, f)
    return out_file


def plot_result(pkl_path, out_path):
    with open(pkl_path, 'rb') as f:
        results = pickle.load(f)

    # 1. 绘制盈利、亏损、0饼状图
    is_profit = [p[-1] for p in results]
    log.info('Profit Num:' + str(len(is_profit)))

    labels = 'Profit', 'Loss', '0'

    sizes = [0, 0, 0]

    for p in is_profit:
        if p > 0:
            sizes[0] += 1
        if p < 0:
            sizes[1] += 1
        else:
            sizes[2] += 1

    explode = (0.1, 0.05, 0.05)

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')
    # plt.legend(prop=font)
    plt.legend()
    out_file = os.path.join(out_path, f'profit_pie_chart.png')
    plt.savefig(out_file)

    # plt.show()

    # 2. 绘制盈利柱状图
    n_bins = 150

    fig, axs = plt.subplots()
    axs.hist(is_profit, bins=n_bins, density=True)
    out_file = os.path.join(out_path, f'profit_his_chart.png')
    plt.savefig(out_file)


def main():
    p_dir = os.getcwd()   # 主目录
    p_data = os.path.join(p_dir, 'data')   # 数据目录
    p_out = os.path.join(p_dir, 'exp')   # 输出目录
    make_dirs(p_data)
    make_dirs(p_out)

    train_time_lst = ['1990-01-01', '2019-11-29']   # 训练起始时间
    test_time_lst = ['2019-12-01', '2019-12-31']  # 测试起始时间
    skip_prep = True   # 是否跳过准备数据
    test_stock_code = 'sh.600036'  # 测试单个股票代码
    init_account_balance = 10000   # 账户初始资金数量
    batch_test_num = 3    # 多股票测试的数量

    # 1. get stock data
    log.info('==== 1. Data Prepare =====')
    train_path, test_path = get_data(p_data, train_time_lst, test_time_lst, skip_prep)

    log.info('==== 2. Test Trade One Stock =====')
    test_a_stock_trade(train_path, test_path, test_stock_code, init_account_balance, out_path=p_out)
    log.info('==== 3. Test Trade Multiple Stock =====')
    pkl_path = multi_stock_trade(train_path, test_path, test_num=batch_test_num, out_path=p_out)
    plot_result(pkl_path, p_out)


if __name__ == '__main__':
    main()
