"""Security regression for the locked HTTP transport used by Requests/SDKs."""

import ssl
from types import SimpleNamespace

from urllib3 import connection
from urllib3._base_connection import ProxyConfig


def test_https_proxy_keeps_its_certificate_verification_policy(monkeypatch):
    """Destination TLS overrides must not disable the proxy's strict policy."""
    proxy_context = ssl.create_default_context()
    conn = connection.HTTPSConnection(
        "proxy.example.test",
        cert_reqs=ssl.CERT_NONE,
        server_hostname="destination.example.test",
        cert_file="destination-client.pem",
        proxy_config=ProxyConfig(proxy_context, True, "proxy.example.test", None),
    )
    handshake = {}
    transport = object()

    def wrap_socket(sock, **kwargs):
        handshake.update(kwargs)
        return SimpleNamespace(socket=sock, is_verified=True)

    # Keep urllib3's policy selection real; replace only the TLS handshake.
    monkeypatch.setattr(connection, "_ssl_wrap_socket_and_match_hostname", wrap_socket)
    assert conn._connect_tls_proxy("proxy.example.test", transport) is transport
    assert handshake["ssl_context"] is proxy_context
    assert handshake["cert_reqs"] == ssl.CERT_REQUIRED
    assert handshake["server_hostname"] == "proxy.example.test"
    assert handshake["assert_hostname"] == "proxy.example.test"
    assert handshake["cert_file"] is None
    assert proxy_context.verify_mode == ssl.CERT_REQUIRED
    assert conn.proxy_is_verified is True
