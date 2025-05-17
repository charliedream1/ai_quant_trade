# 注意

千万注意显卡驱动、CUDA版本、pytorch版本、xformers版本、flash attention2、unsloth版本，否则会出冲突

# 1. CUDA需要12.1以上

12.1以下，会报cuStreamWriteValue32错误

# 2. 网络推理出现 no attribute 'attn_bias'

因为xformers没有安装，或者版本问题。unsloth依赖xformers(据说按flash attention2，不装xfomers也可以，但未验证)，

# 3. flash attention2是否必须装

可以不装，但装了更快
