How to Use:

1. Setup Test conditions in conf/double_ma.yaml
2. Run Command as below

```shell
    python back_tester.py --debug_off \
      --config conf/double_ma.yaml
```

Current Result:

| Risk Indicator | col2 | 
| ---------------- | ------ |
|  total_returns   |  0.097863    |     
|  annal_returns   |  0.051365    |      
|  sharp_ratio     |  0.026636    |      
|  max_withdraw    |  -0.152564    |      
|  sortino_ratio   |  0.088889    |      
|  win_rate        |  0.051365    |      
|  profit_loss_ratio |  0.776881    |      
|  max_con_losses    |  9813.072    |      
