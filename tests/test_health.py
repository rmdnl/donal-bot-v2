from app.core.health import check


def test_core_health():
    status = check()

    assert status.ok is True
    assert status.component == "core"
    assert "foundation" in status.message.lower()
