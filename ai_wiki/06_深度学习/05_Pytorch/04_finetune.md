由于初始化的权重可能会导致模型收敛不佳，且为了加快训练速度，可以预训练模型的权值参数作为
我们自定义模型的初始化参数。在基础模型基础上，针对特定任务在进行调优，这个过程称为 finetune，
更广泛的称之为迁移学习。fintune 的本质其实就是，让我们有一个较好的权重初始化值。

finetune的好处：
- 加快模型收敛
- 往往比重头训能得到一个更好的模型

模型 finetune 一般步骤如下:

- 获取预训练模型的权重（如  imagenet ）；
- 使用预训练模型权重初始化我们的模型，即加载预训练模型权重参数。

模型 finetune 一般有两种情况:
- 数据量少的情况：直接使用预训练模型权重当作特征提取器，只改变模型最后的全连接层。
- 有一定数据量：全网调优比固定层效果好，可以可虑浅层用较低的学习略（底层作为特征提取器），高层用高些的学习率。
- 网络有部分相同：使用自定义网络结构，只有部分网络和预训练模型相同，加载相同的权重，加快训练时间

pytorch使用
1. 直接使用 imagenet 的 resnet50 预训练模型权重当作特征提取器，只改变模型最后的全连接层。代码示例如下:
    ```python
    import torch
    import torchvision.models as models
    
    model = models.resnet50(pretrained=True)
    
    #遍历每一个参数，将其设置为不更新参数，即冻结模型所有参数
    for param in model.parameters():
        param.requires_grad = False
    
    # 只替换最后的全连接层， 改为训练10类，全连接层requires_grad为True
    model.fc = nn.Linear(2048, 10)
    
    print(model.fc) # 这里打印下全连接层的信息
    # 输出结果: Linear(in_features=2048, out_features=10, bias=True)
    ```
2. 使用自定义模型结构，保存某次训练好后比较好的权重用于后续训练 finetune，可节省模型训练时间，示例代码如下:
    ```python
    import torch
    import torchvision.models as models
    
    # 1，保存模型权重参数值
    # 假设已经创建了一个 net = Net()，并且经过训练，通过以下方式保存模型权重值
    torch.save(net.state_dict(), 'net_params.pth')
    # 2，加载模型权重文件
    # load(): Loads an object saved with :func:`torch.save` from a file
    pretrained_dict = torch.load('net_params.pth')
    # 3，初始化模型
    net = Net() # 创建 net
    net_state_dict = net.state_dict() # 获取已创建 net 的 state_dict
    # (可选)将 pretrained_dict 里不属于 net_state_dict 的键剔除掉:
    pretrained_dict_new = {k: v for k, v in pretrained_dict.items() if k in net_state_dict}
    # 用预训练模型的参数字典 对 新模型的参数字典 net_state_dict 进行更新
    net_state_dict.update(pretrained_dict_new)
    # 加载需要的预训练模型参数字典
    net.load_state_dict(net_state_dict)
    ```
   
# 参考
[1] 深度学习炼丹-超参数设定和模型训练, https://mp.weixin.qq.com/s/upps5iZYHzRCZbEZ0wyvBg