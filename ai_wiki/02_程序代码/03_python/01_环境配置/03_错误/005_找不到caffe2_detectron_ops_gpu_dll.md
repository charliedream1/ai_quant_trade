![](.002_找不到caffe2_detectron_ops_gpu_dll_images/找不到caffe2_detectron_ops_gpu.dll.png)

问题：调用pytorch时，找不到anaconda3\lib\site-packages\torch\lib\caffe2_detectron_ops_gpu.dll

1. 原因1：
    - 原因：特别在更新升级时，旧的包里残留的东西，可能没有删除干净
    - 解决：将conda下的anaconda3\lib\site-packages\torch，torch文件夹直接删除

2. 原因2：
    - 原因：没有安装配套版本的CUDA和CUDNN
    - 解决：
        - 前提：安装显卡驱动，并确保版本和CUDA版本配套
        - 方法1：从英伟达官网下载CUDA和Cudnn包进行安装
        - 方法2：方法1可能过于麻烦，可以通过conda直接安装，
                对于cudatoolkit < 11.2，可以通过conda安装来规避。更好版本目前国内镜像没有，
                国外又老是连不上，只能通过方法1
