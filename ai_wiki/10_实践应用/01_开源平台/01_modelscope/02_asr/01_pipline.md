# 使用
The pipeline which contains VAD, ASR, PUNC and NNLM models：

```python
inference_pipeline = pipeline(
    task=Tasks.auto_speech_recognition,
    model='damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
    vad_model='damo/speech_fsmn_vad_zh-cn-16k-common-pytorch',
    punc_model='damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',
    lm_model='damo/speech_transformer_lm_zh-cn-common-vocab8404-pytorch',
    lm_weight=0.15,
    beam_size=10,
)
```

For the Paraformer-large-long, the pipeline defaults to combine VAD, ASR and PUNC models. For example, 
the following pipeline decodes with VAD, ASR and PUNC models.

```python
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

inference_pipeline = pipeline(
    task=Tasks.auto_speech_recognition,
    model='damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
)
```

# 参考
[1] asr长音频pipline, https://github.com/alibaba-damo-academy/FunASR/discussions/134