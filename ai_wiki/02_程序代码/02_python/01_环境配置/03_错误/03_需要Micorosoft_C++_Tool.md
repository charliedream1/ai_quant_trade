# 1. 问题
Windows下安装包，编译时可能报错，提示需要安装Microsoft C++ Build Tools

1. 问题
    ctc-segmentation (因为没有编译环境，所以编译失败)
    ```
    Building wheel for ctc-segmentation (pyproject.toml) ... error
    error: subprocess-exited-with-error
    × Building wheel for ctc-segmentation (pyproject.toml) did not run successfully.
    │ exit code: 1
    ╰─> [12 lines of output]
    running bdist_wheel
    running build
    running build_py 
    creating build
    creating build\lib.win-amd64-cpython-37
    creating build\lib.win-amd64-cpython-37\ctc_segmentation
    copying ctc_segmentation\ctc_segmentation.py -> build\lib.win-amd64-cpython-37\ctc_segmentation
    copying ctc_segmentation\partitioning.py -> build\lib.win-amd64-cpython-37\ctc_segmentation
    copying ctc_segmentation\__init__.py -> build\lib.win-amd64-cpython-37\ctc_segmentation
    running build_ext
    building 'ctc_segmentation.ctc_segmentation_dyn' extension
    error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
    [end of output]
    note: This error originates from a subprocess, and is likely not a problem with pip.
    ERROR: Failed building wheel for ctc-segmentation
    ```

2. 解决方案
安装Microsoft Build Tools for Visual Studio，在 Build Tools 中，安装“使用C++的桌面开发”并确保安装详细信息的两项勾选：MSVC生成工具、windows SDK

# 参考
[1] FunASR安装Wiki, https://github.com/alibaba-damo-academy/FunASR/wiki/Windows%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85