# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/7/5 8:26
# @File     : api_stock_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: abstract class for data interface api
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

from abc import ABC, abstractmethod


class StockDataApi(ABC):
    def __init__(self):
        super().__init__()

    # get dataframe type data
    @abstractmethod
    def get_df_data(self,
                    benchmark: str,
                    stock_id: str,
                    start_time: str,
                    end_time: str,
                    time_freq: str = 'daily',
                    skip_download: bool = True,
                    csv_dir: str = ''
                    ) -> dict:
        """
        :param benchmark: benchmark code for market index
        :param stock_id: stock id for query data
        :param start_time: query start time
        :param end_time: query end time
        :param time_freq: frequency of data, e.g. daily or minutes
        :param skip_download: if csv exist, it will skip download
        :param csv_dir: csv dir to save query data
        :return: query data with dataframe type
        """
        pass

    # @abstractmethod
    # def load_via_csv(self, csv_file_path) -> pd.DataFrame:
    #     pass
