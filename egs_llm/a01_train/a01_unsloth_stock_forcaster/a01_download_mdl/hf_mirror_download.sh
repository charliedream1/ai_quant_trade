export HF_HOME="/mnt/mdl/mdl_zoo"
export HF_ENDPOINT=https://hf-mirror.com
export HF_DATASETS_CACHE='/mnt/mdl/mdl_zoo/cache'

huggingface-cli download --repo-type model  --resume-download \
      --local-dir-use-symlinks False \
      unsloth/Qwen3-0.6B-unsloth-bnb-4bit \
      --local-dir /mnt/mdl/mdl_zoo/unsloth/Qwen3-0.6B-unsloth-bnb-4bit