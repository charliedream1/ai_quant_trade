这个只是相对进程来说吧。你可以弄一个线程池，复用线程

可以弄个threadpool，python 已经给你封装好了

其实你可以先把c++的websocket 弄好，然后封装一下，在python 里调用

kaldifeat依赖PyTorch ，这个依赖有点重。建议试试kaldi-native-fbank, 
这个更加轻量级，在cpu上速度更快，且支持很多平台和架构，比如ios 和android 等。

我写过webrtc c++到python numpy的接口

https://github.com/qmpzzpmq/aec3_raaec 这个有需要可以自取

onnx最通用吧 但是onnx的opset真的一言难尽

opset有点奇怪，我试过，同一个模型，不同opset，rtf不一样

确实不一样。 而且CPU 和GPU 表现非常大
之前有个模型 cpu 跑一个用例 需要550ms
gpu 只需要3ms 
