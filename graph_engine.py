"""Graph construction and numeric propagation for Chaos Weather Dreamer."""

import networkx as nx

import db

EDGE_MULTIPLIERS = {
    "proximity": 0.40,
    "coastal_influence": 0.55,
    "mountain_barrier": -0.25,
    "river_basin": 0.70,
    "wind_corridor": 0.80,
    "urban_heat_island": 0.45,
    "commuter_flow": 0.35,
    "weather_causal": 0.65,
}

RISK_BOUNDS = {
    "flood_risk": (0.0, 1.0),
    "wildfire_smoke_risk": (0.0, 1.0),
    "disruption_score": (0.0, 100.0),
    "mood_score": (0.0, 100.0),
}

# event_type -> (source-node feature deltas per unit severity, propagated features, allowed edge types)
EVENT_RULES = {
    "heavy_rainfall": {
        "deltas": {
            "rainfall_mm": 20.0,
            "humidity_pct": 10.0,
            "flood_risk": 0.35,
            "disruption_score": 25.0,
            "mood_score": -10.0,
        },
        "propagate_features": ["flood_risk", "disruption_score"],
        "edge_types": ["river_basin", "proximity", "commuter_flow", "weather_causal"],
    },
    "urban_heat_spike": {
        "deltas": {
            "temperature_c": 6.0,
            "humidity_pct": -5.0,
            "disruption_score": 15.0,
            "mood_score": -12.0,
        },
        "propagate_features": ["temperature_c", "disruption_score"],
        "edge_types": ["urban_heat_island", "proximity", "commuter_flow"],
    },
    "wildfire_smoke": {
        "deltas": {
            "wildfire_smoke_risk": 0.55,
            "disruption_score": 20.0,
            "mood_score": -15.0,
        },
        "propagate_features": ["wildfire_smoke_risk", "disruption_score"],
        "edge_types": ["wind_corridor", "weather_causal", "proximity"],
    },
    "microclimate_anomaly": {
        "deltas": {
            "temperature_c": 3.0,
            "rainfall_mm": 8.0,
            "wind_speed_kmh": 10.0,
            "flood_risk": 0.15,
            "wildfire_smoke_risk": 0.10,
            "disruption_score": 18.0,
            "mood_score": -8.0,
        },
        "propagate_features": ["disruption_score", "flood_risk", "wildfire_smoke_risk"],
        "edge_types": ["proximity", "commuter_flow", "coastal_influence", "weather_causal"],
    },
    "localized_flash_flood": {
        "deltas": {
            "rainfall_mm": 15.0,
            "flood_risk": 0.40,
            "disruption_score": 30.0,
            "mood_score": -15.0,
        },
        "propagate_features": ["flood_risk", "disruption_score"],
        "edge_types": ["river_basin", "proximity", "commuter_flow"],
    },
    "wind_storm": {
        "deltas": {
            "wind_speed_kmh": 30.0,
            "pressure_hpa": -8.0,
            "disruption_score": 22.0,
            "mood_score": -10.0,
        },
        "propagate_features": ["wind_speed_kmh", "disruption_score"],
        "edge_types": ["wind_corridor", "coastal_influence", "proximity"],
    },
    "cold_snap": {
        "deltas": {
            "temperature_c": -8.0,
            "disruption_score": 15.0,
            "mood_score": -8.0,
        },
        "propagate_features": ["temperature_c", "disruption_score"],
        "edge_types": ["wind_corridor", "proximity", "weather_causal"],
    },
}

DEFAULT_RULE = EVENT_RULES["microclimate_anomaly"]


def load_graph(timestep: int) -> nx.DiGraph:
    """Load nodes, node features, and edges for a given timestep into a directed graph."""
    graph = nx.DiGraph()
    features_by_node = {f["node_id"]: f for f in db.get_features(timestep)}
    for node in db.get_nodes():
        feats = dict(features_by_node.get(node["node_id"], {}))
        feats.pop("id", None)
        feats.pop("timestep", None)
        feats.pop("node_id", None)
        graph.add_node(node["node_id"], **node, **feats)
    for edge in db.get_edges():
        graph.add_edge(
            edge["source_id"],
            edge["target_id"],
            edge_type=edge["edge_type"],
            weight=edge["weight"],
            description=edge["description"],
        )
    return graph


def build_adjacency_list(graph: nx.DiGraph) -> dict:
    """Adjacency list keyed by node name, per the spec format."""
    adjacency = {}
    for source, target, attrs in graph.edges(data=True):
        source_name = graph.nodes[source]["name"]
        adjacency.setdefault(source_name, []).append(
            {
                "target": graph.nodes[target]["name"],
                "edge_type": attrs["edge_type"],
                "weight": attrs["weight"],
                "description": attrs.get("description", ""),
            }
        )
    return adjacency


def clamp_features(features: dict) -> dict:
    for key, (low, high) in RISK_BOUNDS.items():
        if key in features and features[key] is not None:
            features[key] = min(high, max(low, features[key]))
    if features.get("humidity_pct") is not None:
        features["humidity_pct"] = min(100.0, max(0.0, features["humidity_pct"]))
    if features.get("rainfall_mm") is not None:
        features["rainfall_mm"] = max(0.0, features["rainfall_mm"])
    if features.get("wind_speed_kmh") is not None:
        features["wind_speed_kmh"] = max(0.0, features["wind_speed_kmh"])
    return features


def apply_events_and_propagate(graph: nx.DiGraph, events: list[dict]) -> tuple[list[dict], dict]:
    """Apply event deltas to source nodes and propagate through edges.

    Returns (next_features, propagation_log) where propagation_log maps
    node names to short strings describing what reached them.
    """
    next_features = {}
    for node_id, attrs in graph.nodes(data=True):
        next_features[node_id] = {
            "node_id": node_id,
            "temperature_c": attrs.get("temperature_c"),
            "rainfall_mm": attrs.get("rainfall_mm"),
            "humidity_pct": attrs.get("humidity_pct"),
            "wind_speed_kmh": attrs.get("wind_speed_kmh"),
            "pressure_hpa": attrs.get("pressure_hpa"),
            "flood_risk": attrs.get("flood_risk"),
            "wildfire_smoke_risk": attrs.get("wildfire_smoke_risk"),
            "disruption_score": attrs.get("disruption_score"),
            "mood_score": attrs.get("mood_score"),
        }

    propagation_log: dict[str, list[str]] = {}

    for event in events:
        rule = EVENT_RULES.get(event["event_type"], DEFAULT_RULE)
        severity = float(event.get("severity", 1.0))
        source_id = event.get("node_id")
        if source_id is None or source_id not in next_features:
            continue

        source_deltas = {}
        for feature, delta_per_severity in rule["deltas"].items():
            delta = delta_per_severity * severity
            if next_features[source_id][feature] is not None:
                next_features[source_id][feature] += delta
                source_deltas[feature] = delta

        source_name = graph.nodes[source_id]["name"]
        propagation_log.setdefault(source_name, []).append(
            f"direct impact of {event['event_type']} (severity {severity:.2f})"
        )

        for _, target_id, edge_attrs in graph.out_edges(source_id, data=True):
            edge_type = edge_attrs["edge_type"]
            if edge_type not in rule["edge_types"] and edge_type != "mountain_barrier":
                continue
            multiplier = EDGE_MULTIPLIERS.get(edge_type, 0.3)
            factor = edge_attrs["weight"] * multiplier
            if factor <= 0:
                target_name = graph.nodes[target_id]["name"]
                propagation_log.setdefault(target_name, []).append(
                    f"buffered from {source_name} by {edge_type}"
                )
                continue
            for feature in rule["propagate_features"]:
                delta = source_deltas.get(feature)
                if delta is None or next_features[target_id][feature] is None:
                    continue
                next_features[target_id][feature] += delta * factor
            target_name = graph.nodes[target_id]["name"]
            propagation_log.setdefault(target_name, []).append(
                f"received {', '.join(rule['propagate_features'])} from {source_name} "
                f"via {edge_type} (factor {factor:.2f})"
            )

    for node_id in next_features:
        clamp_features(next_features[node_id])
        for key, value in next_features[node_id].items():
            if isinstance(value, float):
                next_features[node_id][key] = round(value, 2)

    flat_log = {name: "; ".join(entries) for name, entries in propagation_log.items()}
    return list(next_features.values()), flat_log


ADJUSTMENT_LIMITS = {
    "temperature_c": 2.0,
    "rainfall_mm": 5.0,
    "humidity_pct": 5.0,
    "wind_speed_kmh": 8.0,
    "pressure_hpa": 3.0,
    "flood_risk": 0.1,
    "wildfire_smoke_risk": 0.1,
    "disruption_score": 8.0,
    "mood_score": 8.0,
}


def apply_llm_adjustments(
    graph: nx.DiGraph, next_features: list[dict], adjustments: list[dict], chaos_level: float
) -> dict:
    """Apply bounded LLM-proposed feature deltas. Returns a log of applied nudges.

    Each delta is clamped to +/- ADJUSTMENT_LIMITS[feature] * (0.5 + chaos_level)
    so the LLM can steer the simulation without breaking it.
    """
    features_by_id = {f["node_id"]: f for f in next_features}
    id_by_name = {attrs["name"]: node_id for node_id, attrs in graph.nodes(data=True)}
    applied: dict[str, list[str]] = {}
    scale = 0.5 + chaos_level
    for adj in adjustments[:5]:
        name = adj.get("node")
        feature = adj.get("feature")
        delta = adj.get("delta")
        node_id = id_by_name.get(name)
        limit = ADJUSTMENT_LIMITS.get(feature)
        if node_id is None or limit is None or not isinstance(delta, (int, float)):
            continue
        target = features_by_id.get(node_id)
        if target is None or target.get(feature) is None:
            continue
        bound = limit * scale
        clamped = min(bound, max(-bound, float(delta)))
        target[feature] = round(target[feature] + clamped, 2)
        clamp_features(target)
        applied.setdefault(name, []).append(
            f"{feature} {clamped:+.2f} ({adj.get('reason', 'LLM adjustment')})"
        )
    return {name: "; ".join(entries) for name, entries in applied.items()}


def top_changed_nodes(graph_before: nx.DiGraph, features_after: list[dict], n: int = 5) -> list[dict]:
    """Rank nodes by total normalized feature change."""
    scales = {
        "temperature_c": 10.0,
        "rainfall_mm": 20.0,
        "humidity_pct": 20.0,
        "wind_speed_kmh": 20.0,
        "pressure_hpa": 10.0,
        "flood_risk": 0.5,
        "wildfire_smoke_risk": 0.5,
        "disruption_score": 30.0,
        "mood_score": 30.0,
    }
    changes = []
    after_by_id = {f["node_id"]: f for f in features_after}
    for node_id, attrs in graph_before.nodes(data=True):
        after = after_by_id.get(node_id)
        if not after:
            continue
        total = 0.0
        details = {}
        for feature, scale in scales.items():
            before_val = attrs.get(feature)
            after_val = after.get(feature)
            if before_val is None or after_val is None:
                continue
            diff = after_val - before_val
            if abs(diff) > 1e-9:
                details[feature] = round(diff, 2)
            total += abs(diff) / scale
        changes.append({"node_id": node_id, "name": attrs["name"], "change_score": round(total, 3), "changes": details})
    changes = [c for c in changes if c["change_score"] > 0]
    changes.sort(key=lambda c: c["change_score"], reverse=True)
    return changes[:n]
