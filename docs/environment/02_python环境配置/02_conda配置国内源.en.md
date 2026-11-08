Last edited: 2023-02-25

# 1. Method

## 1.1 Windows Configuration

Source:
https://github.com/alibaba-damo-academy/FunASR/wiki/Windows%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85

Open Anaconda Prompt and run:

```bash
conda config --set show_channel_urls yes
```

Show the Conda configuration file path:

```bash
conda config --show-sources
```

Open the `.condarc` file under the user directory and replace its content with
the Tsinghua mirror configuration:

```yaml
channels:
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/menpo/
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda/
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/msys2/
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
- http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
show_channel_urls: true
```

# 2. Additional Notes

Reposted from: https://zhuanlan.zhihu.com/p/434356947

Published on 2021-11-29 18:35.

Direct package installation can be slow and is often interrupted, so domestic
mirror sources are useful in mainland China.

## 2.1 Configure Domestic Mirrors for a Local Conda Environment

USTC mirror:

```bash
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/msys2/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/bioconda/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/menpo/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/
```

Aliyun mirror:

```bash
conda config --add channels https://mirrors.aliyun.com/pypi/simple/
```

Douban Python mirror:

```bash
conda config --add channels http://pypi.douban.com/simple/
```

Show the channel URL whenever a package is installed:

```bash
conda config --set show_channel_urls yes
conda config --set always_yes True
```

Show all configured channels:

```bash
conda config --show channels
```

## 2.2 Configure Domestic Mirrors for a Server Conda Environment

Add the Tsinghua mirror:

```bash
conda config --add channels http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/win-64/
```

Note: use `http` instead of `https`, and append `win-64` at the end.

## 2.3 Common Operations

Show configured source files:

```bash
conda config --show-sources
```

Remove a mirror source:

```bash
conda config --remove channels <source-name-or-url>
```

Verify installation:

To make sure PyTorch was installed correctly, run a simple PyTorch example. In
Anaconda Prompt, Miniconda Prompt, or a shell, enter Python:

```bash
python
```

Then run:

```python
import torch
x = torch.rand(5, 3)
print(x)
```

The output should look similar to:

```text
tensor([[0.3380, 0.3845, 0.3217],
      [0.8337, 0.9050, 0.2650],
      [0.2979, 0.7141, 0.9069],
      [0.1449, 0.1132, 0.1375],
      [0.4675, 0.3947, 0.1426]])
```

To check whether PyTorch has GPU and CUDA support enabled, run:

```python
import torch
torch.cuda.is_available()
```

If it returns `True`, the GPU version was installed successfully.

# 3. Manual Package Downloads

NVIDIA-related packages:
https://anaconda.org/nvidia/repo?type=conda&label=main

# References

[1] FunASR installation wiki:
https://github.com/alibaba-damo-academy/FunASR/wiki/Windows%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85

[2] https://blog.csdn.net/taoyu94/article/details/108150892

[3] https://www.bilibili.com/read/cv7476249

[4] https://www.jianshu.com/p/cd9b81f3e886
