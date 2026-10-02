# -*- coding: utf-8 -*-
"""End-to-end run script for a05_test.

The real ``batch_test_transformers.py`` loads a multi-GB LLM from
``/mnt/mdl/...`` that does not exist in this environment. We inject
a fake tokenizer/model that mimics the interface used by the
``Evaluator`` class, then drive the full evaluate flow end-to-end
with a tiny test CSV.

Run from the project root:

    python run_e2e.py
"""
import sys
import shutil
from pathlib import Path
from unittest import mock

PROJ = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJ))


# ---------- 1. Inject fake LLM model + tokenizer into transformers ------
import torch  # noqa: E402


class _EncOut:
    """Mimics the BatchEncoding returned by tokenizer.__call__."""
    def __init__(self, n, L):
        self.input_ids = torch.zeros((n, L), dtype=torch.long)
        self.attention_mask = torch.ones((n, L), dtype=torch.long)
    def to(self, device):
        return self
    def __getitem__(self, key):
        return getattr(self, key)


class FakeTokenizer:
    pad_token_id = 0
    eos_token_id = 1

    def __call__(self, texts, return_tensors=None, padding=False,
                 truncation=False, max_length=None, add_special_tokens=False):
        n = len(texts)
        L = max(len(t) for t in texts)
        return _EncOut(n, L)

    def apply_chat_template(self, msgs, tokenize=False,
                            add_generation_prompt=False, enable_thinking=False):
        return ['fake prompt'] * len(msgs)

    def batch_decode(self, ids, skip_special_tokens=False,
                     clean_up_tokenization_spaces=False):
        # Mimic judge_outputs alternating buy/sell to exercise parsing.
        return ['[上涨]' if i % 2 == 0 else '[下跌]' for i in range(len(ids))]


class FakeModel:
    def to(self, device):
        return self
    def generate(self, input_ids, attention_mask, eos_token_id,
                 pad_token_id, max_new_tokens, **kw):
        n = input_ids.shape[0]
        return torch.cat([input_ids, torch.zeros((n, 1), dtype=torch.long)], dim=1)


fake_mod = mock.MagicMock()
fake_mod.AutoModelForCausalLM.from_pretrained.return_value = FakeModel()
fake_mod.AutoTokenizer.from_pretrained.return_value = FakeTokenizer()
sys.modules['transformers'] = fake_mod


# ---------- 2. Build tiny test CSV --------------------------------------
import pandas as pd
data_dir = PROJ / 'e2e_data'
if data_dir.exists():
    shutil.rmtree(data_dir)
data_dir.mkdir()

test_csv = data_dir / 'test.csv'
df = pd.DataFrame({
    'instruction': ['请预测涨跌'] * 4,
    'input': ['新闻1', '新闻2', '新闻3', '新闻4'],
    'output': ['[上涨]', '[下跌]', '[上涨]', '[下跌]'],
    'deepseek_r1_answers': ['[上涨]', '[下跌]', '[上涨]', '[下跌]'],
})
df.to_csv(test_csv, index=False, encoding='utf-8')


# ---------- 3. Run the actual Evaluator.evaluate via a custom main -----
import batch_test_transformers as bt  # noqa: E402

save_csv = data_dir / 'result.csv'
ev = bt.Evaluator('FAKE_MODEL_PATH')
# evaluate() writes the result CSV but does not return values
ev.evaluate(str(test_csv), str(save_csv), batch_size=2, test_num=4)

assert save_csv.exists(), 'evaluate() did not write result CSV'
result_df = pd.read_csv(save_csv)
assert 'predict' in result_df.columns, 'result CSV missing predict column'
assert 'correct' in result_df.columns, 'result CSV missing correct column'
assert len(result_df) == 4, f'expected 4 rows, got {len(result_df)}'
judged = result_df['predict'].tolist()
assert all(j in ('[上涨]', '[下跌]') for j in judged), \
    f'unexpected judged outputs: {judged}'
print('E2E OK: batch_test_transformers.Evaluator.evaluate ran end-to-end')
print('  judged outputs:', judged)
print('  result csv    ->', save_csv)