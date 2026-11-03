"""Network pinning and configuration updates retain their security semantics."""

import socket
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from src.core.env_file import import_env_file, read_env_values, save_env_value
from src.core.network_policy import network_session, validate_url
from src.core.process_env import process_environment


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://100.100.100.200/",
        "http://[::ffff:169.254.169.254]/",
        "http://user:password@localhost/",
        "file:///etc/passwd",
    ],
)
def test_metadata_and_credential_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url, resolve=True)


def test_hostname_is_checked_after_dns_resolution():
    answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))]
    with patch("src.core.network_policy.socket.getaddrinfo", return_value=answer):
        with pytest.raises(ValueError, match="网络范围"):
            validate_url("http://public-name.invalid/", resolve=True)
    with network_session() as session:
        assert not session.trust_env


def test_private_local_model_services_are_still_allowed():
    _, addresses = validate_url("http://127.0.0.1:8001/v1", resolve=True)
    assert str(addresses[0]) == "127.0.0.1"


def test_configuration_import_validates_all_keys_before_mutating(tmp_path):
    target = tmp_path / ".llm_env"
    source = tmp_path / "upload.env"
    source.write_text("NEW_API_KEY=synthetic\nALL_IN_ONE_CODEX_CLI=untrusted\n", encoding="utf-8")
    with pytest.raises(ValueError, match="不允许"):
        import_env_file(source, target=target, restricted=True)
    assert not target.exists()


def test_parallel_configuration_writes_do_not_lose_values(tmp_path):
    target = tmp_path / ".llm_env"
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda index: save_env_value(f"TEST_{index}_API_KEY", str(index), target), range(8)))
    assert len(read_env_values(target)) == 8


def test_child_process_only_gets_relevant_credentials(monkeypatch):
    monkeypatch.setenv("UNRELATED_PRIVATE_API_KEY", "must-not-leave-parent")
    monkeypatch.setenv("OPENAI_API_KEY", "explicit-provider-key")
    assert "UNRELATED_PRIVATE_API_KEY" not in process_environment("codex")
    assert process_environment("codex")["OPENAI_API_KEY"] == "explicit-provider-key"
    assert "OPENAI_API_KEY" not in process_environment()


def test_unconfigured_encryption_cannot_silently_return_plaintext():
    from src.core.crypto import encrypt_secret, legacy_plaintext_secret

    with pytest.raises(RuntimeError, match="加密凭据"):
        encrypt_secret("synthetic-secret")
    assert encrypt_secret("") == ""
    assert legacy_plaintext_secret("legacy") == "legacy"
