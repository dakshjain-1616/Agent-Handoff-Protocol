"""HandoffBroker for managing handoffs between agents."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .packet import HandoffPacket

logger = logging.getLogger(__name__)

AUDIT_EVENT_SENT = "sent"
AUDIT_EVENT_RECEIVED = "received"
AUDIT_EVENT_EXPIRED = "expired"
AUDIT_EVENT_PURGED = "purged"


class HandoffBroker:
    """
    Manages handoffs between agents in a running system.
    
    Stores sent packets in SQLite and provides send/receive methods
    with automatic timestamp and routing metadata.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the HandoffBroker.
        
        Args:
            db_path: Path to SQLite database. If None, uses in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self._conn: Optional[sqlite3.Connection] = None
        # Guards access to the shared sqlite3 connection across threads.
        # sqlite3 connections aren't thread-safe for concurrent writes even
        # with check_same_thread=False, so every cursor/commit is serialized.
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        cursor = self._conn.cursor()
        
        # Create table for handoff packets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS handoff_packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                packet_json TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                received INTEGER DEFAULT 0,
                received_timestamp TEXT,
                routing_metadata TEXT
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_to_agent 
            ON handoff_packets(to_agent)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_id 
            ON handoff_packets(task_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON handoff_packets(timestamp DESC)
        """)

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                packet_id INTEGER,
                event_type TEXT NOT NULL,
                agent_name TEXT,
                timestamp TEXT NOT NULL,
                details_json TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_packet_id ON audit_log(packet_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_agent_name ON audit_log(agent_name)")

        self._conn.commit()

    def _audit(
        self,
        event_type: str,
        packet_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit log entry."""
        if self._conn is None:
            return
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_log (packet_id, event_type, agent_name, timestamp, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    packet_id,
                    event_type,
                    agent_name,
                    datetime.now(UTC).isoformat(),
                    json.dumps(details) if details else None,
                ),
            )
            self._conn.commit()
    
    def send(
        self,
        packet: HandoffPacket,
        from_agent: str,
        to_agent: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Send a handoff packet from one agent to another.
        
        Args:
            packet: The HandoffPacket to send
            from_agent: Name of the sending agent
            to_agent: Name of the receiving agent
            metadata: Optional routing metadata
            
        Returns:
            ID of the stored packet
        """
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        
        timestamp = datetime.now(UTC).isoformat()
        packet_json = packet.model_dump_json()
        metadata_json = json.dumps(metadata) if metadata else None

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO handoff_packets
                (task_id, from_agent, to_agent, packet_json, timestamp, routing_metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                packet.task_id,
                from_agent,
                to_agent,
                packet_json,
                timestamp,
                metadata_json
            ))

            self._conn.commit()
            packet_id = cursor.lastrowid
        self._audit(
            AUDIT_EVENT_SENT,
            packet_id=packet_id,
            agent_name=from_agent,
            details={
                "task_id": packet.task_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "ttl_seconds": packet.ttl_seconds,
                "expires_at": packet.expires_at.isoformat() if packet.expires_at else None,
            },
        )
        return packet_id

    def receive(
        self,
        agent_name: str,
        mark_received: bool = True
    ) -> Optional[HandoffPacket]:
        """
        Receive the latest packet for an agent.
        
        Args:
            agent_name: Name of the receiving agent
            mark_received: Whether to mark the packet as received
            
        Returns:
            HandoffPacket or None if no packet found
        """
        result = self.receive_with_metadata(agent_name, mark_received)
        if result is None:
            return None
        return result[0]
    
    def receive_with_metadata(
        self,
        agent_name: str,
        mark_received: bool = True
    ) -> Optional[Tuple[HandoffPacket, Dict[str, Any]]]:
        """
        Receive the latest packet for an agent with routing metadata.
        
        Args:
            agent_name: Name of the receiving agent
            mark_received: Whether to mark the packet as received
            
        Returns:
            Tuple of (HandoffPacket, routing_info) or None if no packet found
        """
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT id, task_id, from_agent, to_agent, packet_json,
                       timestamp, received, received_timestamp, routing_metadata
                FROM handoff_packets
                WHERE to_agent = ?
                ORDER BY timestamp DESC
            """, (agent_name,))

            rows = cursor.fetchall()
        row = None
        packet = None
        for candidate in rows:
            try:
                candidate_packet = HandoffPacket.model_validate_json(candidate["packet_json"])
            except Exception as e:
                raise ValueError(f"Failed to parse stored packet: {e}")
            if candidate_packet.is_expired():
                logger.info(
                    "Skipping expired packet id=%s task_id=%s to_agent=%s",
                    candidate["id"], candidate["task_id"], agent_name,
                )
                self._audit(
                    AUDIT_EVENT_EXPIRED,
                    packet_id=candidate["id"],
                    agent_name=agent_name,
                    details={"task_id": candidate["task_id"], "reason": "skipped_on_receive"},
                )
                continue
            row = candidate
            packet = candidate_packet
            break

        if row is None:
            return None

        # Build routing info
        routing_info = {
            "id": row["id"],
            "task_id": row["task_id"],
            "from_agent": row["from_agent"],
            "to_agent": row["to_agent"],
            "sent_timestamp": row["timestamp"],
            "received": bool(row["received"]),
            "received_timestamp": row["received_timestamp"],
            "metadata": json.loads(row["routing_metadata"]) if row["routing_metadata"] else None,
        }
        
        # Mark as received if requested
        if mark_received and not row["received"]:
            received_time = datetime.now(UTC).isoformat()
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    UPDATE handoff_packets
                    SET received = 1, received_timestamp = ?
                    WHERE id = ?
                """, (received_time, row["id"]))
                self._conn.commit()
            routing_info["received_timestamp"] = received_time
            routing_info["received"] = True
            self._audit(
                AUDIT_EVENT_RECEIVED,
                packet_id=row["id"],
                agent_name=agent_name,
                details={"task_id": row["task_id"], "from_agent": row["from_agent"]},
            )

        # Store routing metadata in packet.working_memory under '_routing' key
        if packet.working_memory is None:
            packet.working_memory = {}
        packet.working_memory["_routing"] = routing_info

        return packet, routing_info

    def receive_all(
        self,
        agent_name: str,
        unread_only: bool = False,
        mark_received: bool = True
    ) -> List[Tuple[HandoffPacket, Dict[str, Any]]]:
        """
        Receive all packets for an agent.
        
        Args:
            agent_name: Name of the receiving agent
            unread_only: Whether to only return unread packets
            mark_received: Whether to mark packets as received
            
        Returns:
            List of (HandoffPacket, routing_info) tuples
        """
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")

        with self._lock:
            cursor = self._conn.cursor()

            if unread_only:
                cursor.execute("""
                    SELECT id, task_id, from_agent, to_agent, packet_json,
                           timestamp, received, received_timestamp, routing_metadata
                    FROM handoff_packets
                    WHERE to_agent = ? AND received = 0
                    ORDER BY timestamp ASC
                """, (agent_name,))
            else:
                cursor.execute("""
                    SELECT id, task_id, from_agent, to_agent, packet_json,
                           timestamp, received, received_timestamp, routing_metadata
                    FROM handoff_packets
                    WHERE to_agent = ?
                    ORDER BY timestamp ASC
                """, (agent_name,))

            rows = cursor.fetchall()
        results = []

        for row in rows:
            try:
                packet = HandoffPacket.model_validate_json(row["packet_json"])
            except Exception as e:
                raise ValueError(f"Failed to parse stored packet: {e}")
            
            routing_info = {
                "id": row["id"],
                "task_id": row["task_id"],
                "from_agent": row["from_agent"],
                "to_agent": row["to_agent"],
                "sent_timestamp": row["timestamp"],
                "received": bool(row["received"]),
                "received_timestamp": row["received_timestamp"],
                "metadata": json.loads(row["routing_metadata"]) if row["routing_metadata"] else None,
            }
            
            # Mark as received if requested
            if mark_received and not row["received"]:
                received_time = datetime.now(UTC).isoformat()
                with self._lock:
                    cur2 = self._conn.cursor()
                    cur2.execute("""
                        UPDATE handoff_packets
                        SET received = 1, received_timestamp = ?
                        WHERE id = ?
                    """, (received_time, row["id"]))
                    self._conn.commit()
                routing_info["received_timestamp"] = received_time
                routing_info["received"] = True

            results.append((packet, routing_info))

        return results
    
    def get_packet_history(
        self,
        task_id: str,
        include_received: bool = True
    ) -> List[Tuple[HandoffPacket, Dict[str, Any]]]:
        """
        Get the full handoff history for a task.
        
        Args:
            task_id: The task ID to query
            include_received: Whether to include received packets
            
        Returns:
            List of (HandoffPacket, routing_info) tuples ordered by timestamp
        """
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")

        with self._lock:
            cursor = self._conn.cursor()

            if include_received:
                cursor.execute("""
                    SELECT id, task_id, from_agent, to_agent, packet_json,
                           timestamp, received, received_timestamp, routing_metadata
                    FROM handoff_packets
                    WHERE task_id = ?
                    ORDER BY timestamp ASC
                """, (task_id,))
            else:
                cursor.execute("""
                    SELECT id, task_id, from_agent, to_agent, packet_json,
                           timestamp, received, received_timestamp, routing_metadata
                    FROM handoff_packets
                    WHERE task_id = ? AND received = 0
                    ORDER BY timestamp ASC
                """, (task_id,))

            rows = cursor.fetchall()
        results = []
        
        for row in rows:
            try:
                packet = HandoffPacket.model_validate_json(row["packet_json"])
            except Exception as e:
                raise ValueError(f"Failed to parse stored packet: {e}")
            
            routing_info = {
                "id": row["id"],
                "task_id": row["task_id"],
                "from_agent": row["from_agent"],
                "to_agent": row["to_agent"],
                "sent_timestamp": row["timestamp"],
                "received": bool(row["received"]),
                "received_timestamp": row["received_timestamp"],
                "metadata": json.loads(row["routing_metadata"]) if row["routing_metadata"] else None,
            }
            
            results.append((packet, routing_info))
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the broker.
        
        Returns:
            Dictionary with statistics
        """
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")

        with self._lock:
            cursor = self._conn.cursor()

            # Total packets
            cursor.execute("SELECT COUNT(*) FROM handoff_packets")
            total_packets = cursor.fetchone()[0]

            # Received packets
            cursor.execute("SELECT COUNT(*) FROM handoff_packets WHERE received = 1")
            received_packets = cursor.fetchone()[0]

            # Pending packets
            cursor.execute("SELECT COUNT(*) FROM handoff_packets WHERE received = 0")
            pending_packets = cursor.fetchone()[0]

            # Unique agents
            cursor.execute("SELECT COUNT(DISTINCT from_agent) FROM handoff_packets")
            from_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT to_agent) FROM handoff_packets")
            to_agents = cursor.fetchone()[0]

            # Unique tasks
            cursor.execute("SELECT COUNT(DISTINCT task_id) FROM handoff_packets")
            unique_tasks = cursor.fetchone()[0]
        
        return {
            "total_packets": total_packets,
            "received_packets": received_packets,
            "pending_packets": pending_packets,
            "unique_from_agents": from_agents,
            "unique_to_agents": to_agents,
            "unique_tasks": unique_tasks,
        }
    
    def purge_expired(self) -> int:
        """Delete all expired packets from the store. Returns count deleted."""
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT id, task_id, to_agent, packet_json FROM handoff_packets")
            rows = cursor.fetchall()
            expired: List[Tuple[int, str, Optional[str]]] = []
            for row in rows:
                try:
                    p = HandoffPacket.model_validate_json(row["packet_json"])
                except Exception:
                    continue
                if p.is_expired():
                    expired.append((row["id"], row["task_id"], row["to_agent"]))
            for pid, _tid, _agent in expired:
                cursor.execute("DELETE FROM handoff_packets WHERE id = ?", (pid,))
            self._conn.commit()
        # Audit outside the main lock (audit takes the lock internally).
        for pid, tid, agent in expired:
            self._audit(
                AUDIT_EVENT_PURGED,
                packet_id=pid,
                agent_name=agent,
                details={"task_id": tid},
            )
        return len(expired)

    def stats(self) -> Dict[str, int]:
        """Return {total, pending, expired, delivered} counts."""
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT id, packet_json, received FROM handoff_packets"
            )
            rows = cursor.fetchall()
        total = 0
        pending = 0
        expired = 0
        delivered = 0
        for row in rows:
            total += 1
            try:
                p = HandoffPacket.model_validate_json(row["packet_json"])
                is_exp = p.is_expired()
            except Exception:
                is_exp = False
            if is_exp:
                expired += 1
            if bool(row["received"]):
                delivered += 1
            else:
                pending += 1
        return {
            "total": total,
            "pending": pending,
            "expired": expired,
            "delivered": delivered,
        }

    def get_audit_log(
        self,
        packet_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return audit log entries sorted newest-first."""
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        clauses: List[str] = []
        params: List[Any] = []
        if packet_id is not None:
            clauses.append("packet_id = ?")
            params.append(packet_id)
        if agent_name is not None:
            clauses.append("agent_name = ?")
            params.append(agent_name)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = (
            f"SELECT id, packet_id, event_type, agent_name, timestamp, details_json "
            f"FROM audit_log {where} ORDER BY id DESC LIMIT ?"
        )
        params.append(limit)
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append({
                "id": row["id"],
                "packet_id": row["packet_id"],
                "event_type": row["event_type"],
                "agent_name": row["agent_name"],
                "timestamp": row["timestamp"],
                "details": json.loads(row["details_json"]) if row["details_json"] else None,
            })
        return results

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()
