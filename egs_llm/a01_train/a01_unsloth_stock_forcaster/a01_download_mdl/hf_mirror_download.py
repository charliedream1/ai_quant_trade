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
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = '/mnt/mdl/mdl_zoo'
os.environ['HF_DATASETS_CACHE'] = '/mnt/mdl/mdl_zoo/cache'

from retrying import retry
from huggingface_hub import snapshot_download

MAX_TRY_NUM = 50


@retry(stop_max_attempt_number=MAX_TRY_NUM)
def download(repo_id, cache_dir, repo_type):
    snapshot_download(repo_id=repo_id,
                      cache_dir=cache_dir,
                      repo_type=repo_type,
                      local_dir_use_symlinks=False)


def main():
    """
    Problem:
        local_dir_use_symlinks=False doesn't work, it still uses links,
        however, by using cli command, it has no this issue.
    """
    # 1. sometimes it will fail, try several times
    # 2. it supports continue downloading
    # 3. it's much faster than git clone
    repo_id = 'unsloth/Qwen3-0.6B-unsloth-bnb-4bit'
    # repo_id = 'unsloth/Qwen3-8B-unsloth-bnb-4bit'
    cache_dir = '/mnt/mdl/mdl_zoo'
    repo_type = "model"   # dataset, model
    download(repo_id, cache_dir, repo_type)


if __name__ == '__main__':
    main()
