"""Tests for the audit log."""

from datetime import datetime, timedelta, UTC

import pytest

from agent_handoff_protocol import HandoffBroker, HandoffPacket


def _make_packet(task_id="task_audit", ttl_seconds=None, expires_at=None) -> HandoffPacket:
    kwargs = {"task_id": task_id, "original_goal": "goal"}
    if ttl_seconds is not None:
        kwargs["ttl_seconds"] = ttl_seconds
    if expires_at is not None:
        kwargs["expires_at"] = expires_at
    return HandoffPacket(**kwargs)


class TestAuditSend:
    def test_send_logs_sent_event(self):
        broker = HandoffBroker()
        pid = broker.send(_make_packet("t1"), "A", "B")
        events = broker.get_audit_log(event_type="sent")
        assert len(events) == 1
        assert events[0]["event_type"] == "sent"
        assert events[0]["packet_id"] == pid
        assert events[0]["agent_name"] == "A"
        broker.close()


class TestAuditReceive:
    def test_receive_logs_received_event(self):
        broker = HandoffBroker()
        broker.send(_make_packet("t2"), "A", "B")
        broker.receive("B")
        events = broker.get_audit_log(event_type="received")
        assert len(events) == 1
        assert events[0]["agent_name"] == "B"
        broker.close()


class TestAuditExpired:
    def test_expired_logs_expired_event(self):
        broker = HandoffBroker()
        past = datetime.now(UTC) - timedelta(seconds=1)
        broker.send(_make_packet("t3", expires_at=past), "A", "B")
        # Attempt to receive -> triggers expired audit
        assert broker.receive("B") is None
        events = broker.get_audit_log(event_type="expired")
        assert len(events) == 1
        assert events[0]["agent_name"] == "B"
        broker.close()


class TestAuditFilters:
    def test_filter_by_agent_and_event_and_packet_id(self):
        broker = HandoffBroker()
        pid1 = broker.send(_make_packet("t4"), "A", "B")
        pid2 = broker.send(_make_packet("t5"), "X", "Y")
        broker.receive("B")

        # agent filter
        a_events = broker.get_audit_log(agent_name="A")
        assert all(e["agent_name"] == "A" for e in a_events)
        assert len(a_events) == 1

        # event_type filter
        received = broker.get_audit_log(event_type="received")
        assert len(received) == 1
        assert received[0]["event_type"] == "received"

        # packet_id filter
        pid2_events = broker.get_audit_log(packet_id=pid2)
        assert all(e["packet_id"] == pid2 for e in pid2_events)
        assert len(pid2_events) == 1
        broker.close()


class TestAuditLimit:
    def test_limit_respected_and_newest_first(self):
        broker = HandoffBroker()
        for i in range(5):
            broker.send(_make_packet(f"t{i}"), "A", "B")

        events = broker.get_audit_log(limit=3)
        assert len(events) == 3
        # Newest-first: ids are descending
        ids = [e["id"] for e in events]
        assert ids == sorted(ids, reverse=True)
        broker.close()


class TestAuditPurge:
    def test_purge_logs_purged_events(self):
        broker = HandoffBroker()
        past = datetime.now(UTC) - timedelta(seconds=1)
        broker.send(_make_packet("p1", expires_at=past), "A", "B")
        broker.send(_make_packet("p2", expires_at=past), "A", "B")
        broker.purge_expired()
        events = broker.get_audit_log(event_type="purged")
        assert len(events) == 2
        broker.close()
