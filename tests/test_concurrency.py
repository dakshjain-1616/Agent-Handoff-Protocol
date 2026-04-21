"""Concurrent broker access regression tests."""
import threading

from agent_handoff_protocol import HandoffBroker, HandoffPacket


def test_concurrent_sends_do_not_drop_packets():
    broker = HandoffBroker()
    errors: list[str] = []

    def worker(i: int) -> None:
        try:
            for j in range(10):
                pkt = HandoffPacket(task_id=f"c-{i}-{j}", original_goal="concurrent send")
                broker.send(pkt, from_agent=f"sender-{i}", to_agent=f"recv-{i}")
        except Exception as e:  # pragma: no cover - surfaced via assertion below
            errors.append(repr(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"concurrent send raised: {errors}"
    stats = broker.stats()
    assert stats["total"] == 30, stats

    total = 0
    for i in range(3):
        items = broker.receive_all(f"recv-{i}", mark_received=True)
        assert len(items) == 10
        total += len(items)
    assert total == 30

    broker.close()
