"""Small CPU neural ensemble with training-only feature standardization."""

from __future__ import annotations

from threading import Lock
from typing import Any

import numpy as np
import torch
from torch import nn

TRAIN_LOCK = Lock()


class NeuralEnsemble:
    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params
        self.networks: list[nn.Module] = []
        self.mean: Any = None
        self.scale: Any = None
        self.target_scale = 1.0

    def fit(self, features: Any, targets: Any) -> NeuralEnsemble:
        self.mean = features.mean(axis=0)
        self.scale = np.maximum(features.std(axis=0), np.finfo(np.float32).eps)
        self.target_scale = max(float(np.std(targets)), float(np.finfo(np.float32).eps))
        x = torch.as_tensor((features - self.mean) / self.scale, dtype=torch.float32)
        y = torch.as_tensor(targets / self.target_scale, dtype=torch.float32).reshape(-1, 1)
        with TRAIN_LOCK:
            threads = torch.get_num_threads()
            try:
                torch.set_num_threads(int(self.params["threads"]))
                with torch.random.fork_rng(devices=[]):
                    self.networks = [self._fit_member(x, y, int(seed)) for seed in self.params["seeds"]]
            finally:
                torch.set_num_threads(threads)
        return self

    def _fit_member(self, x: Any, y: Any, seed: int) -> nn.Module:
        torch.manual_seed(seed)
        layers: list[nn.Module] = []
        width = x.shape[1]
        for hidden in self.params["hidden_sizes"]:
            layers.extend([nn.Linear(width, int(hidden)), nn.ReLU()])
            width = int(hidden)
        layers.append(nn.Linear(width, 1))
        network = nn.Sequential(*layers)
        optimizer = torch.optim.AdamW(
            network.parameters(),
            lr=float(self.params["learning_rate"]),
            weight_decay=float(self.params["weight_decay"]),
        )
        for _ in range(int(self.params["epochs"])):
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(network(x), y)
            loss.backward()
            optimizer.step()
        network.eval()
        return network

    def predict(self, features: Any) -> Any:
        values = torch.as_tensor((features - self.mean) / self.scale, dtype=torch.float32)
        with torch.no_grad():
            outputs = [network(values).numpy().reshape(-1) for network in self.networks]
        return np.mean(outputs, axis=0) * self.target_scale


def build_model(params: dict[str, Any]) -> NeuralEnsemble:
    return NeuralEnsemble(params)
