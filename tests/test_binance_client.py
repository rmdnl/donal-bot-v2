from app.exchange.binance_client import BinanceClient


def test_client_has_expected_defaults():
    client = BinanceClient()

    assert client.base_url == "https://api.binance.com"
    assert client.timeout == 10.0
    assert client.max_retries == 3
