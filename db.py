"""SQLite persistence layer for Chaos Weather Dreamer."""

import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chaos_weather.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    node_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT,
    node_type TEXT DEFAULT 'location',
    latitude REAL,
    longitude REAL,
    elevation_m REAL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS node_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    timestep INTEGER NOT NULL,
    temperature_c REAL,
    rainfall_mm REAL,
    humidity_pct REAL,
    wind_speed_kmh REAL,
    pressure_hpa REAL,
    flood_risk REAL,
    wildfire_smoke_risk REAL,
    disruption_score REAL,
    mood_score REAL,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
    UNIQUE(node_id, timestep)
);

CREATE TABLE IF NOT EXISTS edges (
    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    edge_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    description TEXT,
    FOREIGN KEY (source_id) REFERENCES nodes(node_id),
    FOREIGN KEY (target_id) REFERENCES nodes(node_id)
);

CREATE TABLE IF NOT EXISTS latent_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestep INTEGER NOT NULL,
    encoder_layer_1 TEXT,
    encoder_layer_2 TEXT,
    temporal_state TEXT,
    spatial_state TEXT,
    stochastic_state TEXT,
    decoded_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestep INTEGER NOT NULL,
    node_id INTEGER,
    event_type TEXT NOT NULL,
    severity REAL DEFAULT 1.0,
    description TEXT,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
);
"""

FEATURE_COLUMNS = [
    "temperature_c",
    "rainfall_mm",
    "humidity_pct",
    "wind_speed_kmh",
    "pressure_hpa",
    "flood_risk",
    "wildfire_smoke_risk",
    "disruption_score",
    "mood_score",
]


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def clear_simulation_state() -> None:
    """Remove all timesteps > 0, latent states, and events (keeps seed data)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM node_features WHERE timestep > 0")
        conn.execute("DELETE FROM latent_states")
        conn.execute("DELETE FROM events")


def get_nodes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM nodes ORDER BY node_id").fetchall()
    return [dict(r) for r in rows]


def get_node_by_name(name: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def get_features(timestep: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM node_features WHERE timestep = ? ORDER BY node_id",
            (timestep,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_edges() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM edges ORDER BY edge_id").fetchall()
    return [dict(r) for r in rows]


def get_events(timestep: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT e.*, n.name AS node_name FROM events e
               LEFT JOIN nodes n ON n.node_id = e.node_id
               WHERE e.timestep = ? ORDER BY e.event_id""",
            (timestep,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_event(timestep: int, node_id: int | None, event_type: str, severity: float, description: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO events (timestep, node_id, event_type, severity, description) VALUES (?, ?, ?, ?, ?)",
            (timestep, node_id, event_type, severity, description),
        )


def save_events(timestep: int, events: list[dict]) -> None:
    for ev in events:
        insert_event(
            timestep,
            ev.get("node_id"),
            ev.get("event_type", "unknown"),
            float(ev.get("severity", 1.0)),
            ev.get("description", ""),
        )


def save_features(timestep: int, features: list[dict]) -> None:
    with get_connection() as conn:
        for feat in features:
            values = [feat.get(c) for c in FEATURE_COLUMNS]
            conn.execute(
                f"""INSERT OR REPLACE INTO node_features
                    (node_id, timestep, {', '.join(FEATURE_COLUMNS)})
                    VALUES (?, ?, {', '.join('?' for _ in FEATURE_COLUMNS)})""",
                [feat["node_id"], timestep] + values,
            )


def save_latent_state(
    timestep: int,
    encoder_layer_1: str,
    encoder_layer_2: str,
    temporal_state: str,
    spatial_state: str,
    stochastic_state: dict,
    decoded_summary: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO latent_states
               (timestep, encoder_layer_1, encoder_layer_2, temporal_state,
                spatial_state, stochastic_state, decoded_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                timestep,
                encoder_layer_1,
                encoder_layer_2,
                temporal_state,
                spatial_state,
                json.dumps(stochastic_state),
                decoded_summary,
            ),
        )


def get_latent_states() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM latent_states ORDER BY timestep, id").fetchall()
    return [dict(r) for r in rows]


def get_max_timestep() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(timestep) AS mt FROM node_features").fetchone()
    return row["mt"] if row and row["mt"] is not None else 0
