import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk.circuit_breaker import CircuitBreaker

def test_opens_and_recovers():
    cb = CircuitBreaker(max_failures=3, cooldown_seconds=0.2)
    for _ in range(3): cb.record_failure()
    assert not cb.allow()
    time.sleep(0.3)
    assert cb.allow()

def test_success_resets():
    cb = CircuitBreaker(max_failures=2, cooldown_seconds=10)
    cb.record_failure(); cb.record_success(); cb.record_failure()
    assert cb.allow()
