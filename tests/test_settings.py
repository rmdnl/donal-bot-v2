from app.config.settings import Settings


def test_defaults_to_testnet():
    settings = Settings()

    assert settings.binance_base_url == (
        "https://testnet.binance.vision"
    )
    assert settings.bot_env == "testnet"
    assert settings.is_testnet is True


def test_empty_credentials_are_detected():
    settings = Settings(
        binance_api_key="",
        binance_api_secret="",
    )

    try:
        settings.validate_credentials()
        assert False
    except ValueError as exc:
        assert "missing" in str(exc)


def test_testnet_credentials_validate():
    settings = Settings(
        binance_api_key="test-key",
        binance_api_secret="test-secret",
    )

    settings.validate_credentials()
