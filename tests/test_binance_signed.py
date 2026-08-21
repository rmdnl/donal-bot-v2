from app.config.settings import Settings
from app.exchange.binance_signed import BinanceSignedClient


def make_client():
    settings = Settings(
        binance_api_key="test-key",
        binance_api_secret="secret",
        bot_env="testnet",
    )

    return BinanceSignedClient(settings)


def test_builds_signed_request():
    client = make_client()

    url, params = client.build_signed_request(
        "/api/v3/account"
    )

    assert url == "https://testnet.binance.vision/api/v3/account"
    assert params["recvWindow"] == "5000"
    assert "timestamp" in params
    assert "signature" in params
    assert len(params["signature"]) == 64


def test_signature_changes_with_parameters():
    client = make_client()

    _, first = client.build_signed_request(
        "/api/v3/account",
        {"foo": "one"},
    )

    _, second = client.build_signed_request(
        "/api/v3/account",
        {"foo": "two"},
    )

    assert first["signature"] != second["signature"]


def test_missing_credentials_rejected():
    settings = Settings(
        binance_api_key="",
        binance_api_secret="",
        bot_env="testnet",
    )

    client = BinanceSignedClient(settings)

    try:
        client.build_signed_request("/api/v3/account")
        assert False
    except ValueError as exc:
        assert "missing" in str(exc)
