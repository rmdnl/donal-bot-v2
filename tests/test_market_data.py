import pandas as pd

from app.exchange.market_data import MarketData


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get(self, path, params):
        self.calls.append((path, params))
        return self.rows


def make_row(open_time, close_time):
    return [
        open_time,
        "100",
        "110",
        "90",
        "105",
        "1000",
        close_time,
        "105000",
        100,
        "500",
        "52500",
        "0",
    ]


def test_klines_normalizes_dataframe():
    client = FakeClient(
        [
            make_row(1000, 1999),
            make_row(2000, 2999),
        ]
    )

    data = MarketData(client)
    frame = data.klines("btcusdt", "1m", 2)

    assert len(frame) == 2
    assert frame["close"].tolist() == [105.0, 105.0]
    assert str(frame["open_time"].dt.tz) == "UTC"
    assert client.calls[0][0] == "/api/v3/klines"


def test_klines_validates_limit():
    client = FakeClient([])
    data = MarketData(client)

    try:
        data.klines("BTCUSDT", "1m", 1001)
        assert False
    except ValueError as exc:
        assert "between 1 and 1000" in str(exc)


def test_closed_klines_removes_open_candle():
    client = FakeClient(
        [
            make_row(1000, 1999),
            make_row(2000, 2999),
        ]
    )

    data = MarketData(client)

    frame = data.closed_klines(
        "BTCUSDT",
        "1m",
        2,
        now=pd.Timestamp(2500, unit="ms", tz="UTC"),
    )

    assert len(frame) == 1
    assert frame.iloc[0]["open_time"] == pd.Timestamp(
        1000,
        unit="ms",
        tz="UTC",
    )
