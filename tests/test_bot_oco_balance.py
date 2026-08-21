from types import SimpleNamespace
from unittest.mock import Mock

from core.bot import Bot


def make_bot(client):
    cfg = {
        "strategy": {
            "donal": {},
            "mean_reversion": {},
            "multi_regime_enabled": False,
            "breakeven": {
                "enabled": False,
                "trigger_atr_multiplier": 1.0,
            },
            "time_stop": {
                "enabled": False,
            },
        },
        "kill_switch": {
            "lookback_minutes": 5,
            "crash_threshold_15m": 0.05,
            "volume_baseline_minutes": 20,
            "volume_spike_multiplier": 3.0,
        },
        "trading": {
            "symbols": ["BTCUSDT"],
            "poll_interval_seconds": 1,
        },
        "circuit_breaker": {
            "api_max_failures": 3,
            "api_cooldown_seconds": 60,
        },
        "risk": {},
    }

    return Bot(
        client=client,
        states=Mock(),
        risk=Mock(),
        breaker=Mock(),
        breakeven=Mock(),
        notifier=Mock(),
        cfg=cfg,
        dry_run=False,
    )


def test_sync_position_keeps_position_when_balance_is_locked_by_oco():
    client = Mock()

    quantity = 0.01

    client.get_asset_balance.return_value = {
        "free": 0.0,
        "locked": quantity,
        "total": quantity,
    }

    client.get_oco_status.return_value = {
        "orderListStatus": "EXECUTING",
    }

    bot = make_bot(client)

    state = SimpleNamespace(
        symbol="BTCUSDT",
        in_position=True,
        quantity=quantity,
        entry_price=100000.0,
        entry_atr=100.0,
        sl_price=99000.0,
        tp_price=102000.0,
        oco_order_list_id=123,
        entry_ts=None,
        strategy="TEST",
        breakeven_triggered=False,
        kill_switch_cooldown_until=None,
    )

    result = bot.sync_position("BTCUSDT", state)

    assert result is state
    assert result.in_position is True
    assert result.quantity == quantity
    client.get_asset_balance.assert_called_once_with("BTC")
    client.get_oco_status.assert_called_once_with("BTCUSDT", 123)
