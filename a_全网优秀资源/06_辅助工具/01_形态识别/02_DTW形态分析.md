# 1. DTW简介

**DTW（动态时间规整）**是一种用于**衡量两条时间序列相似性**的算法，即使这两条序列在**时间轴上有伸缩、平移或速度差异**，也能准确地对齐。

# 2. 开源项目汇总

1. DTW-CNN
    - Github (0 stars): https://github.com/a-niva/DTW-CNN?utm_source=chatgpt.com
    - 一个全面的算法交易框架系统，利用深度学习嵌入和向量相似性搜索来识别市场模式并预测资产回报。该框架结合了神经时间序列编码、基于 FAISS 的相似性匹配、动态时间扭曲 （DTW） 和先进的聚类技术，为算法交易和投资组合管理提供定量见解。

2. Pattern-Based Trading System
    - Github (1 stars): https://github.com/stefanjuang/pattern-trading-system?utm_source=chatgpt.com
    - 基于模式的交易系统是一个基于 Python 的库，用于分析金融时间序列数据。它利用软动态时间扭曲 （Soft-DTW） 和贝叶斯优化等先进算法来识别有利可图的交易模式。该系统比较买入并持有和活跃交易策略，以最大化回报，确保没有数据泄露或自我匹配。

3. time_series_query_by_DTW
    - Github (1 stars):https://github.com/ShawniLee/time_series_query_by_DTW?utm_source=chatgpt.com
    - 时间序列查询匹配器是一个高效的子序列搜索系统，专为多维时间序列数据而设计。它可以在与给定查询序列相似的长时间序列（上下文序列）中快速定位段，即使这些段包含噪声、缩放变化或时移。
    - 该项目利用动态时间扭曲（DTW）算法实现灵活的相似性计算，并通过各种优化技术，包括下采样、早期放弃策略和LB_Keogh下界修剪，显着提高了搜索效率。

4. PyTorchDTW
    - Github (2 stars):https://github.com/MicahSee/PyTorchDTW?utm_source=chatgpt.com
    - 支持GPU加速

5. fastdtw —— 高效动态时间规整算法实现
    - 项目地址:
      - Gitee (0 stars): https://gitcode.com/gh_mirrors/fa/fastdtw
      - Github (834 stars): https://github.com/slaypni/fastdtw
    - fastdtw 是一个基于 Python 的库，提供了一个优化的动态时间规整（Dynamic Time Warping, DTW）算法实现，名为 FastDTW。该算法能在保持高效率的同时，实现近乎最优的时间序列配对，其时间复杂度和空间复杂度均为线性级别，即 O(N)。
    - 参考文献：Stan Salvador, 和 Philip Chan. "FastDTW: 实现线性时间和空间的精确动态时间规整." 智能数据分析 11.5 (2007): 561-580.

6. Pattern based trading with similarity measures
    - Github (6 stars): https://github.com/ka5par/dtw?utm_source=chatgpt.com
    - 模式匹配交易算法，比较不同相似性度量（如DTW/TWED/LCSS/Corr）的性能。 通过相似性测量计算的距离用作 KNN 的输入。方法基于 Nagakawa、Imamura 和 Yoshida 的论文1 & 2.


