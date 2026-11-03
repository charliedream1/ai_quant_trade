"""Checksummed native model and numeric tensor artifacts; no Python object pickle."""

import json
from hashlib import sha256
from importlib import import_module
from threading import RLock
from typing import Any

import numpy as np

from src.core.config import PROJECT_ROOT, get_settings
from src.core.timeutil import utc_now_iso

from .config import fail

MODEL_LOCK = RLock()


class NativeBooster:
    def __init__(self, booster):
        self.booster = booster

    def predict(self, values):
        return self.booster.predict(values)


class ModelArtifacts:
    def __init__(self):
        self.root = (get_settings().data_dir / "models/pipelines").resolve()
        if not self.root.is_relative_to(PROJECT_ROOT.resolve()):
            raise fail("invalid", "model artifact root")
        self.root.mkdir(parents=True, exist_ok=True)

    def metadata(self, key: str) -> dict[str, Any] | None:
        with MODEL_LOCK:
            return self._metadata(key)

    def _metadata(self, key: str) -> dict[str, Any] | None:
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise fail("invalid", "model id")
        path = self.root / (key[:24] + ".json")
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value["id"] != key:
            raise fail("invalid", "model digest collision")
        file = (self.root / value["file"]).resolve()
        if (
            not file.is_relative_to(self.root)
            or not file.is_file()
            or sha256(file.read_bytes()).hexdigest() != value["sha256"]
        ):
            raise fail("invalid", "model checksum")
        return value

    def save(self, key: str, model: Any, backend: str, params: dict[str, Any], fit: dict[str, Any]) -> dict[str, Any]:
        with MODEL_LOCK:
            existing = self._metadata(key)
            return existing or self._save(key, model, backend, params, fit)

    def _save(self, key: str, model: Any, backend: str, params: dict[str, Any], fit: dict[str, Any]) -> dict[str, Any]:
        extension = {"lightgbm": "txt", "xgboost": "ubj", "mlp": "npz"}[backend]
        file = self.root / (key[:24] + "." + extension)
        if backend == "lightgbm":
            model.model.booster_.save_model(str(file))
        elif backend == "xgboost":
            model.save_model(str(file))
        else:
            arrays = {"mean": model.mean, "scale": model.scale, "target_scale": np.asarray(model.target_scale)}
            for index, network in enumerate(model.networks):
                arrays.update(
                    {f"n{index}_{name}": tensor.detach().cpu().numpy() for name, tensor in network.state_dict().items()}
                )
            np.savez_compressed(file, **arrays)
        metadata = {
            "id": key,
            "backend": backend,
            "params": params,
            "fit": fit,
            "created_at": utc_now_iso(),
            "file": file.name,
            "sha256": sha256(file.read_bytes()).hexdigest(),
            "format": extension,
        }
        (self.root / (key[:24] + ".json")).write_text(
            json.dumps(metadata, ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
        return metadata

    def load(self, metadata: dict[str, Any]) -> Any:
        current = self.metadata(metadata["id"])
        if current != metadata:
            raise fail("invalid", "model metadata")
        file = self.root / metadata["file"]
        backend = metadata["backend"]
        if backend == "lightgbm":
            return NativeBooster(import_module("lightgbm").Booster(model_file=str(file)))
        if backend == "xgboost":
            model = import_module("src.strategy.models.xgboost_backend").build_model(metadata["params"])
            model.load_model(str(file))
            return model
        torch = import_module("torch")
        model = import_module("src.strategy.models.neural_backend").build_model(metadata["params"])
        with np.load(file, allow_pickle=False) as arrays:
            model.mean = arrays["mean"].copy()
            model.scale = arrays["scale"].copy()
            model.target_scale = float(arrays["target_scale"])
            for index, _ in enumerate(metadata["params"]["seeds"]):
                layers = []
                width = len(model.mean)
                for hidden in metadata["params"]["hidden_sizes"]:
                    layers.extend([torch.nn.Linear(width, hidden), torch.nn.ReLU()])
                    width = hidden
                layers.append(torch.nn.Linear(width, 1))
                network = torch.nn.Sequential(*layers)
                network.load_state_dict(
                    {name: torch.from_numpy(arrays[f"n{index}_{name}"].copy()) for name in network.state_dict()}
                )
                network.eval()
                model.networks.append(network)
        return model
