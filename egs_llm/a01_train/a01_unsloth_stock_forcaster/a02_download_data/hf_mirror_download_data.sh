export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/mnt/data
export HF_DATASETS_CACHE=/mnt/data/cache

# finGPT提供数据，覆盖预训练、微调、DPO、推理训练
#huggingface-cli download --repo-type dataset  --resume-download --local-dir-use-symlinks False FinGPT/fingpt-forecaster-sz50-20230201-20240101 --local-dir /mnt/data/fingpt-forecaster-sz50-20230201-20240101
#huggingface-cli download --repo-type dataset  --resume-download --local-dir-use-symlinks False FinGPT/fingpt-forecaster-sz50-20230201-20240101 --local-dir /mnt/data/fingpt-forecaster-sz50-20230201-20240101
#huggingface-cli download --repo-type dataset  --resume-download --local-dir-use-symlinks False FinGPT/fingpt-forecaster-dow30-202305-202405 --local-dir /mnt/data/fingpt-forecaster-dow30-202305-202405
huggingface-cli download --repo-type dataset  --resume-download --local-dir-use-symlinks False IDEA-FinAI/Finance-R1-Reasoning --local-dir /mnt/data/Finance-R1-Reasoning
#huggingface-cli download --repo-type dataset  --resume-download --local-dir-use-symlinks False pmoe7/SP_500_Stocks_Data-ratios_news_price_10_yrs --local-dir /mnt/SP_500_Stocks_Data-ratios_news_price_10_yrs
#huggingface-cli download --repo-type dataset  --resume-download --local-dir-use-symlinks False seeyssimon/sujet-finance-instruct-human-preference-13k --local-dir /mnt/data/sujet-finance-instruct-human-preference-13k
