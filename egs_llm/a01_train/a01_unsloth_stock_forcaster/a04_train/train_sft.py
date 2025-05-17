# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2025/5/12 23:05
# @File     : edit_active_excel.py
# @Project  : main
# Copyright (c) Personal 2025 liyi
# Function Description:
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from unsloth import FastLanguageModel
import torch
import pandas as pd
from datasets import load_dataset
from datasets import Dataset
from trl import SFTTrainer, SFTConfig


# 1. Initialization
work_path = '/mnt/data/Finance-R1-Reasoning'
file_path = os.path.join(work_path, 'train.csv')
reasoning_dataset = Dataset.from_csv(file_path)
mdl_path = '/mnt/mdl/mdl_zoo/unsloth/Qwen3-0.6B-unsloth-bnb-4bit'
save_lora_path = '/mnt/mdl/out/unsloth/Qwen3-0.6B-unsloth-bnb-4bit-lora'
save_merged_path = '/mnt/mdl/out/unsloth/Qwen3-0.6B-unsloth-bnb-16bit-merged'
data_random_sample = -1  # -1 means no random sample


def generate_conversation(examples):
    instructions = examples['instruction']
    inputs = examples['input']
    thinks = examples['thinks']
    outputs = examples['output']

    conversations = []
    for instruct, in_query, think, output  in zip(instructions, inputs, thinks, outputs):
        conversations.append([
            {"role": "user", "content": '###新闻###\n' + in_query +
                                        '\n\n###任务###\n' + instruct},
            {"role": "assistant", "content": '<think>\n' + think + '\n</think>\n\n' + output},
        ])
    return { "conversations": conversations, }

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = mdl_path,
    max_seq_length = 8076,   # Context length - can be longer, but uses more memory
    load_in_4bit = True,     # 4bit uses much less memory
    load_in_8bit = False,    # A bit more accurate, uses 2x memory
    full_finetuning = False, # We have full finetuning now!
    # token = "hf_...",      # use one if using gated models
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 32,           # Choose any number > 0! Suggested 8, 16, 32, 64, 128
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 32,  # Best to choose alpha = rank or rank*2
    lora_dropout = 0, # Supports any, but = 0 is optimized
    bias = "none",    # Supports any, but = "none" is optimized
    # [NEW] "unsloth" uses 30% less VRAM, fits 2x larger batch sizes!
    use_gradient_checkpointing = "unsloth", # True or "unsloth" for very long context
    random_state = 3407,
    use_rslora = True,   # We support rank stabilized LoRA
    loftq_config = None,  # And LoftQ
)

reasoning_conversations = tokenizer.apply_chat_template(
    reasoning_dataset.map(generate_conversation, batched = True)["conversations"],
    tokenize = False,
)

data = pd.concat([
    pd.Series(reasoning_conversations),
])
if data_random_sample > 0:
    print(f"Randomly sampling {data_random_sample} examples.")
    data = data.sample(data_random_sample, random_state = 3407)
    data = data.reset_index(drop = True)

data.name = "text"
combined_dataset = Dataset.from_pandas(pd.DataFrame(data))
combined_dataset = combined_dataset.shuffle(seed = 3407)

# 2. train model
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = combined_dataset,
    eval_dataset = None, # Can set up evaluation!
    args = SFTConfig(
        dataset_text_field = "text",
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4, # Use GA to mimic batch size!
        warmup_steps = 5,
        num_train_epochs = 1, # Set this for 1 full training run.
        # max_steps = 20,
        learning_rate = 2e-5, # Reduce to 2e-5 for long training runs
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        report_to = "none", # Use this for WandB etc
    ),
)

# @title Show current memory stats
gpu_stats = torch.cuda.get_device_properties(0)
start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
print(f"{start_gpu_memory} GB of memory reserved.")

trainer_stats = trainer.train()

# @title Show final memory and time stats
used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
used_percentage = round(used_memory / max_memory * 100, 3)
lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
print(
    f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training."
)
print(f"Peak reserved memory = {used_memory} GB.")
print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
print(f"Peak reserved memory % of max memory = {used_percentage} %.")
print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")

# save lora model
print(f'save lora to: {save_lora_path}')
model.save_pretrained(save_lora_path)  # Local saving
tokenizer.save_pretrained(save_lora_path)

# Merge to 16bit for VLLM
print(f'save merged model to: {save_merged_path}')
model.save_pretrained_merged(save_merged_path, tokenizer, save_method = "merged_16bit",)
# model.push_to_hub_merged("hf/model", tokenizer, save_method = "merged_16bit", token = "")

# Merge to 4bit
# print(f'save merged model to: {save_merged_path}')
# if not use force, it gives out error, and it has error of during inference
# model.save_pretrained_merged(save_merged_path, tokenizer, save_method = "merged_4bit_forced",)

# GGUF 8bit Q8_0
# model.save_pretrained_gguf("model", tokenizer,)
# Save to 16bit GGUF
# model.save_pretrained_gguf("model", tokenizer, quantization_method = "f16")
# Save to q4_k_m GGUF
# model.save_pretrained_gguf("model", tokenizer, quantization_method = "q4_k_m")
# model.push_to_hub_gguf(
#         "hf/model", # Change hf to your username!
#         tokenizer,
#         quantization_method = ["q4_k_m", "q8_0", "q5_k_m",],
#         token = "", # Get a token at https://huggingface.co/settings/tokens
#     )
