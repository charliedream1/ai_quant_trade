# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/8/13 22:20
# @File     : parallel_jobs.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
# Function Description: multi process demo
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

"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
在pycharm里，debug模式可以正常输出，run模式无输出(不确定原因)
但在windows下通过命令行，运行正常
解决方法：网上查询可能由于pycharm不支持multiprocess交互导致，
因此，请在命令行或者debug模式下运行
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""
import multiprocessing


# method为多次调用的方法
def method(num, para, index):
    print('Processing {} {}/{}'.format(para, index, num))
    pass


def job(x):
    return x * x


def main():
    # 1. first job
    print('1. first job')
    pool = multiprocessing.Pool(processes=2)
    params = ['param1', 'param2', 'param3', 'param4', 'param5']
    total_num = len(params)
    for i, param in enumerate(params):
        args = [total_num, param, i]
        pool.apply_async(method, args=tuple(args))
    pool.close()
    pool.join()

    # 2. 2nd job
    # *** 问题：linux可能正常，windows下错误
    # 如下缺少close和join，可能导致错误
    # 如下通过Pycharm run模式运行
    # 如下方法在debug模式报错，run模式会报pickle错误，可能有数据类型不能被反序列化
    # 应该是说一个数据结构，比如二叉树之类，序列化以后会变成一个char数组或者一个
    # string字符串这样，方便你存到文件里面或者通过网络传输。然后要恢
    # 复的时候就是“反序列化”，把文件里读出来/从网络收到的char数组或
    # 者string恢复成一棵二叉树或者其他什么东西。

    # ** 解决方案：
    #  官网中给出解释说明：pickle模块不能序列化lambda function，
    #  故我们需要自行定义函数，实现序列化

    print('2. 2nd job')
    pool = multiprocessing.Pool(processes=3)
    res = [pool.apply_async(job, args=(i,)) for i in range(3)]
    print([r.get() for r in res])


if __name__ == '__main__':
    main()
