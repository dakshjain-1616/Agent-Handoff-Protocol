"""Tests for Packet TTL and expiry."""

import time
from datetime import datetime, timedelta, UTC

import pytest

from agent_handoff_protocol import HandoffBroker, HandoffPacket


def _make_packet(task_id: str = "task_ttl", ttl_seconds=None, expires_at=None) -> HandoffPacket:
    kwargs = {"task_id": task_id, "original_goal": "goal"}
    if ttl_seconds is not None:
        kwargs["ttl_seconds"] = ttl_seconds
    if expires_at is not None:
        kwargs["expires_at"] = expires_at
    return HandoffPacket(**kwargs)


class TestPacketTTLDefaults:
    """TTL fields default to None, expires_at unaffected."""

    def test_default_ttl_is_none(self):
        p = _make_packet()
        assert p.ttl_seconds is None
        assert p.expires_at is None
        assert p.is_expired() is False


class TestExpiresAtAutoFill:
    """ttl_seconds auto-fills expires_at via validator."""

    def test_ttl_seconds_fills_expires_at(self):
        p = _make_packet(ttl_seconds=60)
        assert p.expires_at is not None
        # expires_at should be roughly now + 60s
        delta = p.expires_at - datetime.now(UTC)
        assert timedelta(seconds=55) <= delta <= timedelta(seconds=65)

    def test_explicit_expires_at_preserved(self):
        target = datetime.now(UTC) + timedelta(hours=1)
        p = _make_packet(expires_at=target)
        assert p.expires_at == target
        assert p.ttl_seconds is None


class TestReceiveSkipsExpired:
    """Broker.receive must skip expired packets."""

    def test_expired_packet_skipped_by_receive(self):
        broker = HandoffBroker()
        # Force expiry in the past
        past = datetime.now(UTC) - timedelta(seconds=1)
        expired_packet = _make_packet(task_id="expired", expires_at=past)
        broker.send(expired_packet, from_agent="A", to_agent="B")

        assert broker.receive("B") is None
        broker.close()

    def test_non_expired_still_delivered(self):
        broker = HandoffBroker()
        fresh = _make_packet(task_id="fresh", ttl_seconds=300)
        broker.send(fresh, from_agent="A", to_agent="B")

        got = broker.receive("B")
        assert got is not None
        assert got.task_id == "fresh"
        broker.close()

    def test_receive_picks_fresh_when_mixed(self):
        broker = HandoffBroker()
        past = datetime.now(UTC) - timedelta(seconds=1)
        broker.send(_make_packet(task_id="old", expires_at=past), "A", "B")
        # fresh packet sent after, so DESC order yields fresh first
        broker.send(_make_packet(task_id="fresh", ttl_seconds=300), "A", "B")

        got = broker.receive("B")
        assert got is not None
        assert got.task_id == "fresh"
        broker.close()


class TestPurgeExpired:
    def test_purge_expired_returns_count(self):
        broker = HandoffBroker()
        past = datetime.now(UTC) - timedelta(seconds=1)
        broker.send(_make_packet(task_id="e1", expires_at=past), "A", "B")
        broker.send(_make_packet(task_id="e2", expires_at=past), "A", "B")
        broker.send(_make_packet(task_id="fresh", ttl_seconds=300), "A", "B")

        purged = broker.purge_expired()
        assert purged == 2

        # Calling again should return 0
        assert broker.purge_expired() == 0
        broker.close()


class TestBrokerStats:
    def test_stats_counts(self):
        broker = HandoffBroker()
        past = datetime.now(UTC) - timedelta(seconds=1)
        broker.send(_make_packet(task_id="fresh1", ttl_seconds=300), "A", "B")
        broker.send(_make_packet(task_id="fresh2", ttl_seconds=300), "A", "C")
        broker.send(_make_packet(task_id="expired", expires_at=past), "A", "D")

        # Deliver one
        got = broker.receive("B")
        assert got is not None

        stats = broker.stats()
        assert stats["total"] == 3
        assert stats["delivered"] == 1
        assert stats["pending"] == 2
        assert stats["expired"] == 1
        broker.close()
