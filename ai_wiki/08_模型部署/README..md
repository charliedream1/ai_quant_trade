&emsp;&emsp;此部分主要讲解模型部署工具的使用，部署常见的设备有CPU-X86/CPU-ARM/GPU。通过工具可以规避C/C++手写
神经网络前向代码，大大减少开发量。CPU侧首选bolt, 如果按照通用性优选onnx-runtime，GPU侧首选TensorRT。

&emsp;&emsp;CPU常见工具：
* onnx-runtime: 微软出品，应用非常广泛，onnx是目前所有模型的一个中转类型
    * 优点：
        * 只要Tensorflow或Torch能够转换从ONNX（可能存在不支持的算子），基本模型精度都能对上，其余工具即便能转换成功，
          可能也会存在非常见模型出现精度对不上的问题。
        * 提供各种后端和设备支持，如CUDA和TensorRT登
        * 推理速度比libtorch快约30%
        * 库仅有19M
        * 协议商用良好
    * 缺点：不支持x86侧avx指令集加速

* libtorch: pytorch的C++版本
    * 优点：pytorch的所有模型可以完美支持
    * 缺点：
        * pytorch需要按照jit script要求编写，不规范的写法会导致jit无法导出
        * 包过大，冗余过多
        * 存在内存泄露，不确定之后版本是否会解决
        * 1.5版本后包含GPL协议，商用不友好

* nccn: 腾讯出品，维护广泛
    * Git: https://github.com/Tencent/ncnn
    * 优点：
        * 支持的算子多，可从torch直接导出模型
  
* bolt：华为诺亚出品
    * 优点：
        * 库仅有5M，适合端侧部署
        * 支持x86侧avx指令集加速

&emsp;&emsp;GPU常见工具： 
* TensorRT: 英伟达推出的GPU加速工具
    * 优点：
        * 比onnx-runtime的CUDA版本快很多
    * 缺点：
        * 存在较多不支持算子
        * 文档使用不详，使用较为复杂
        
* onnx-runtime: 
    * 优点：
        * 支持各类后端，如CUDA/TensorRT，方便统一接口
    * 缺点：
        * 使用TensorRT后端是，对版本要求较高，不灵活
