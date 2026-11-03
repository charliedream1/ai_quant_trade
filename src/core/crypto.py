"""Masking and explicit compatibility with legacy plaintext credential fields.

Current credentials are environment references, not encrypted database values.
"""


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


def encrypt_secret(value: str) -> str:
    if value:
        raise RuntimeError("未配置加密凭据保管器，请使用环境变量引用，不允许伪装为加密存储")
    return ""


def decrypt_secret(value: str) -> str:
    """Legacy compatibility only: this function does not decrypt ciphertext."""
    return legacy_plaintext_secret(value)


def legacy_plaintext_secret(value: str) -> str:
    """Read an old in-memory profile; persistent rows migrate to env references."""
    return value or ""
