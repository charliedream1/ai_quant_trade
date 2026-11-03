"""Credential-bearing HTTP targets use validated, pinned destinations and TLS names."""

import ipaddress
import socket
from urllib.parse import parse_qsl, urlsplit

import requests
from requests.adapters import HTTPAdapter

from src.core.redaction import SENSITIVE
from src.core.security_config import security_config


def validate_url(url: str, *, resolve: bool = False):
    policy = security_config()["network"]
    value = urlsplit(url)
    if value.scheme not in policy["allowed_schemes"] or not value.hostname or value.username or value.password:
        raise ValueError("连接地址须为不含账户信息的HTTP(S)地址")
    if any(SENSITIVE.search(key) for key, _ in parse_qsl(value.query)):
        raise ValueError("连接凭据请通过受保护的请求头或环境引用配置，不放入URL")
    port = value.port or (443 if value.scheme == "https" else 80)
    addresses = []
    try:
        addresses = [ipaddress.ip_address(value.hostname)]
    except ValueError:
        if resolve:
            addresses = [
                ipaddress.ip_address(row[4][0])
                for row in socket.getaddrinfo(value.hostname, port, type=socket.SOCK_STREAM)
            ]
    for address in addresses:
        normalized = (
            address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped else address
        )
        if (
            str(normalized) in policy["denied_addresses"]
            or normalized.is_unspecified
            or normalized.is_multicast
            or normalized.is_link_local
        ):
            raise ValueError("连接目标不在允许的网络范围内")
    return value, sorted(set(addresses), key=lambda address: address.version)


class DestinationAdapter(HTTPAdapter):
    def __init__(self, *args, public_only: bool = False, **kwargs):
        self.public_only = public_only
        super().__init__(*args, **kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        if any((proxies or {}).values()):
            raise ValueError("凭据连接须使用直接连接；代理需单独登记可信网络策略")
        parsed, addresses = validate_url(request.url, resolve=True)
        if self.public_only and any(not address.is_global for address in addresses):
            raise ValueError("文档下载仅允许公共网络地址")
        if not addresses:
            raise ValueError("连接目标没有可用地址")
        host, options = self.build_connection_pool_key_attributes(request, verify, cert)
        host["host"] = str(addresses[0])
        request.headers["Host"] = parsed.netloc
        if parsed.scheme == "https":
            options.update(server_hostname=parsed.hostname, assert_hostname=parsed.hostname)
        return self.poolmanager.connection_from_host(**host, pool_kwargs=options)


def network_session(*, public_only: bool = False) -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.mount("http://", DestinationAdapter(public_only=public_only))
    session.mount("https://", DestinationAdapter(public_only=public_only))
    return session
