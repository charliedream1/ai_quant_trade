# 注意事项

# 1. 安装所需库
    ```shell
    pip install -r requirements.txt
    ```   
    
    - 如果windows，且使用ElegantRL库，需要安装Microsoft C++ Build Tools (大约需要2.5G空间)    
      https://visualstudio.microsoft.com/visual-cpp-build-tools/   
      安装Microsoft Build Tools for Visual Studio，
      在 Build Tools 中，安装“使用C++的桌面开发”并确保安装详细信息的两项勾选：MSVC生成工具、windows SDK

# 潜在问题及不足
1. 训练和测试不一致：测试中引入了波动率及阈值
2. 模拟环境中没有考虑滑点值
3. 模拟环境没有考虑股票停牌的信息

# 常见问题
## 1. 无法复现论文结果
参考：https://github.com/AI4Finance-Foundation/FinRL-Tutorials/issues/43  

- 问题：论文中的结果无法复现，自己训得比网站给的预训练模型性能差很多  
- 原因：由于强化学习不稳定，建议调参，或者多训练几遍

## 2. 'numpy.float64' object has no attribute 'values'
读取训练数据，所有股票均混在了一个csv表里，格式如下
```
索引     日期          股票
 0      2009-01-02    苹果
 0      2009-01-02    亚马逊
 1      2009-01-05    苹果
 1      2009-01-05    亚马逊
```

注意：必须保持上述该格式，同样的索引下至少有2个数据，否则会报错，
原因：
  1. 在finrl/meta/env_stock_trading/env_stocktrading.py的
     _initiate_state函数中self.data.close.values.tolist()，
     在404行，要求self.data.close必须是二维数组
  2. 而finrl/meta/env_stock_trading/env_stocktrading.py的
     __init__的64行self.data = self.df.loc[self.day, :]，
     如果索引顺序排，0，1，2。。。，会导致只取到一个行数，一维
     数据传入导致第1点中所述的问题
     （因此，如果只有一支股票时，需要把索引全部改成一样的，当然
     这种情况几乎不存在，也可以暂时忽略）
     
解决方法：
1. 降低numpy版本
2. 把数据改成二维的，即（10，）-》（1，10） （改完是否存在回测不完整性，没有详细验证）
3. 保持最上方所示的数据格式（推荐）