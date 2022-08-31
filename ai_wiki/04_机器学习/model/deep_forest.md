# 1. 概述
&emsp;&emsp;Deep Forest是大名鼎鼎的周志华教授于2017年发表的机器学习算法。
该算法结合了传统机器学习和深度学习的思想，使得传统机器学习的性能逼近深度学习，
且能达到更快速训练的效果。

论文：
* Deep Forest: Towards an Alternative to Deep Neural Networks∗
* https://arxiv.org/pdf/1702.08835v2.pdf

&emsp;&emsp;原始的官方实现代码，该代码仓已不再维护。如果想使用多粒度扫描，
更好的处理结构化数据，如图片，请使用原始代码仓。
* Github: https://github.com/kingfengji/gcForest

&emsp;&emsp;代码目前迁至如下代码仓，新的代码着重提升效率和易用性:
* Github: https://github.com/LAMDA-NJU/Deep-Forest
* 文档：https://deep-forest.readthedocs.io/en/latest/index.html
* AISTATS 2019 PPT讲义：https://aistats.org/aistats2019/0-AISTATS2019-slides-zhi-hua_zhou.pdf
* 会议：https://www.ijcai.org/proceedings/2017/0497.pdf
* 期刊：https://academic.oup.com/nsr/article-pdf/6/1/74/30336169/nwy108.pdf


# 2. 使用
&emsp;&emsp;[**注意: 依赖numpy < 1.20.0，但使用1.22.0版本以下的numpy存在安全问题Bug**]

```shell
pip install deep-forest
```

# 2.1 分类问题

```python

from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from deepforest import CascadeForestClassifier

X, y = load_digits(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=1)
model = CascadeForestClassifier(random_state=1)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred) * 100
print("\nTesting Accuracy: {:.3f} %".format(acc))
# >>> Testing Accuracy: 98.667 %
```
```shell
[2022-08-07 07:51:01.746] Start to fit the model:
[2022-08-07 07:51:01.746] Fitting cascade layer = 0 
[2022-08-07 07:51:02.684] layer = 0  | Val Acc = 97.996 % | Elapsed = 0.938 s
[2022-08-07 07:51:02.693] Fitting cascade layer = 1 
[2022-08-07 07:51:03.551] layer = 1  | Val Acc = 98.144 % | Elapsed = 0.858 s
[2022-08-07 07:51:03.561] Fitting cascade layer = 2 
[2022-08-07 07:51:04.262] layer = 2  | Val Acc = 97.921 % | Elapsed = 0.701 s
[2022-08-07 07:51:04.262] Early stopping counter: 1 out of 2
[2022-08-07 07:51:04.270] Fitting cascade layer = 3 
[2022-08-07 07:51:04.949] layer = 3  | Val Acc = 97.476 % | Elapsed = 0.678 s
[2022-08-07 07:51:04.949] Early stopping counter: 2 out of 2
[2022-08-07 07:51:04.949] Handling early stopping
[2022-08-07 07:51:04.949] The optimal number of layers: 2
[2022-08-07 07:51:04.952] Start to evalute the model:
[2022-08-07 07:51:04.952] Evaluating cascade layer = 0 
[2022-08-07 07:51:05.019] Evaluating cascade layer = 1 

Testing Accuracy: 98.667 %
```

# 2.2 回归问题
```python
from sklearn.datasets import load_boston
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

from deepforest import CascadeForestRegressor

X, y = load_boston(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=1)
model = CascadeForestRegressor(random_state=1)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
print("\nTesting MSE: {:.3f}".format(mse))
# >>> Testing MSE: 8.068
```

```shell
[2022-08-07 07:51:05.141] Start to fit the model:
[2022-08-07 07:51:05.141] Fitting cascade layer = 0 
[2022-08-07 07:51:05.634] layer = 0  | Val MSE = 13.34540 | Elapsed = 0.492 s
[2022-08-07 07:51:05.639] Fitting cascade layer = 1 
[2022-08-07 07:51:06.182] layer = 1  | Val MSE = 10.88445 | Elapsed = 0.543 s
[2022-08-07 07:51:06.183] Fitting cascade layer = 2 
[2022-08-07 07:51:06.664] layer = 2  | Val MSE = 12.78401 | Elapsed = 0.481 s
[2022-08-07 07:51:06.664] Early stopping counter: 1 out of 2
[2022-08-07 07:51:06.664] Fitting cascade layer = 3 
[2022-08-07 07:51:07.168] layer = 3  | Val MSE = 15.41706 | Elapsed = 0.504 s
[2022-08-07 07:51:07.168] Early stopping counter: 2 out of 2
[2022-08-07 07:51:07.168] Handling early stopping
[2022-08-07 07:51:07.168] The optimal number of layers: 2
[2022-08-07 07:51:07.177] Start to evalute the model:
[2022-08-07 07:51:07.177] Evaluating cascade layer = 0 
[2022-08-07 07:51:07.211] Evaluating cascade layer = 1 

Testing MSE: 8.068
```

# 2.3 模型保存和加载
* 保存模型
```python
model.save(MODEL_DIR)
```

* 加载模型
```python
new_model = CascadeForestClassifier()
new_model.load(MODEL_DIR)
```


# 3. API
# 3.1 分类接口
参考：https://deep-forest.readthedocs.io/en/latest/api_reference.html#cascadeforestclassifier

deepforest.CascadeForestClassifier(n_bins=255, bin_subsample=200000, bin_type='percentile', max_layers=20, criterion='gini', n_estimators=2, n_trees=100, max_depth=None, min_samples_split=2, min_samples_leaf=1, use_predictor=False, predictor='forest', predictor_kwargs={}, backend='custom', n_tolerant_rounds=2, delta=1e-05, partial_mode=False, n_jobs=None, random_state=None, verbose=1)

* fit(X, y[, sample_weight])
  Build a deep forest using the training data.
* predict_proba(X)
  Predict class probabilities for X.
* predict(X)
  Predict class for X.
* clean()
  Clean the buffer created by the model.
* get_estimator(layer_idx, est_idx, estimator_type)
  Get estimator from a cascade layer in the deep forest.
* get_layer_feature_importances(layer_idx)
  Return the feature importances of layer_idx-th cascade layer.
  Backend需要为'sklearn'时才生效。
* load(dirname)
  Load the model from the directory dirname.
* save([dirname])
  Save the model to the directory dirname.
* set_estimator(estimators[, n_splits])
  Specify the custom base estimators for cascade layers.
* set_predictor(predictor)
  Specify the custom predictor concatenated to deep forest.

# 3.2 回归接口
参考： https://deep-forest.readthedocs.io/en/latest/api_reference.html#cascadeforestregressor

deepforest.CascadeForestRegressor(n_bins=255, bin_subsample=200000, bin_type='percentile', max_layers=20, criterion='mse', n_estimators=2, n_trees=100, max_depth=None, min_samples_split=2, min_samples_leaf=1, use_predictor=False, predictor='forest', predictor_kwargs={}, backend='custom', n_tolerant_rounds=2, delta=1e-05, partial_mode=False, n_jobs=None, random_state=None, verbose=1

* fit(X, y[, sample_weight])
  Build a deep forest using the training data. 输入会被转为np.int8，
  sample_weight: (numpy.ndarray of shape (n_samples,)
* predict(X)
  Predict regression target for X.
* clean()
  Clean the buffer created by the model.
* get_estimator(layer_idx, est_idx, estimator_type)
  Get estimator from a cascade layer in the deep forest.
* get_layer_feature_importances(layer_idx)
  Return the feature importances of layer_idx-th cascade layer.
* load(dirname)
  Load the model from the directory dirname.
* save([dirname])
  Save the model to the directory dirname.
* set_estimator(estimators[, n_splits])
  Specify the custom base estimators for cascade layers.
* set_predictor(predictor)
  Specify the custom predictor concatenated to deep forest.


# 4. 参数调优指南
参考：https://deep-forest.readthedocs.io/en/latest/parameters_tunning.html

# 4.1 模型准确率优化
# 4.1.1 提升模型复杂度
[**注意：模型会根据验证集，自动选择最佳的模型层数复杂度，
如果自己设置，将会禁用自动选择功能。如果参数设的过小，有可能造成很深的层数**]
* n_estimators: Specify the number of estimators in each cascade layer.
* n_trees: Specify the number of trees in each estimator.
max_layers: Specify the maximum number of cascade layers.

# 4.1.2 增加预测器
&emsp;&emsp;除了增加模型复杂度，也可以增加预测器，
如random forest or gradient boosting decision tree (GBDT)。
该方法将使用deep forest提取特征，来训练预测器。

注意：如果使用xgboost或lightGBM请先安装。

* use_predictor: Decide whether to use the predictor concatenated to the deep forest.
* predictor: Specify the type of the predictor, should be one of "forest", "xgboost", "lightgbm".

# 4.2 模型加速
# 4.2.1 并行训练
n_jobs：设定并行数，-1是全部使用

# 4.2.2 更少的分割
* n_bins: Specify the number of feature discrete bins. A smaller value means fewer splitting cut-offs will be considered, should be an integer in the range [2, 255].
* bin_type:
    * Specify the binning type. Setting its value to "interval" enables less splitting cut-offs to be considered on dense intervals where the feature values accumulate.
    * If "percentile", each bin will have approximately the same number of distinct feature values.
    * If "interval", each bin will have approximately the same size.
* partial_mode：数据量很大时，建议选True，数据会被部分导出到Buffer，使用时再导入

# 4.3 降低模型复杂度
* max_depth: Specify the maximum depth of tree. None indicates no constraint.
* min_samples_leaf: Specify the minimum number of samples required to be at a leaf node. The smallest value is 1.
* n_estimators: Specify the number of estimators in each cascade layer.
* n_trees: Specify the number of trees in each estimator.
* n_tolerant_rounds: Specify the number of tolerant rounds when handling early stopping. The smallest value is 1.

# 5. 性能对比
&emsp;&emsp;对比5种常见的树类模型，权衡速度和性能，lightGBM最好，性能上
Deep Forest平均性能最好。Histogram-based GBDT (e.g., HGBDT, XGB HIST, LightGBM)
速度更快，因为一般模型深度更浅。数据维度更好时，random forest and deep forest更快。

* Random Forest: An efficient implementation of Random Forest in Scikit-Learn
* HGBDT: Histogram-based GBDT in Scikit-Learn
* XGBoost EXACT: The vanilla version of XGBoost
* XGBoost HIST: The histogram optimized version of XGBoost
* LightGBM: Light Gradient Boosting Machine

# 6. 深入分析原理
![df21_architecture](img/df21_architecture.png)

