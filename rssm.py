"""RSSM-inspired core: temporal, spatial, and stochastic LLM layers."""

import json
import random
from dataclasses import dataclass

import networkx as nx

from graph_engine import EDGE_MULTIPLIERS, build_adjacency_list
from llm_client import call_llm
from prompts import SPATIAL_LAYER_PROMPT, STOCHASTIC_LAYER_PROMPT, TEMPORAL_LAYER_PROMPT


@dataclass
class LatentState:
    timestep: int
    temporal_state: str
    spatial_state: str
    stochastic_state: dict


def temporal_layer(prev_latent_state: LatentState | None, current_encoder_summary: str, events: list[dict]) -> str:
    """Summarize changes over time and likely momentum."""
    prev_text = (
        f"Previous temporal state: {prev_latent_state.temporal_state}\n"
        f"Previous spatial state: {prev_latent_state.spatial_state}\n"
        f"Previous shock: {json.dumps(prev_latent_state.stochastic_state)}"
        if prev_latent_state
        else "No previous latent state. This is the first timestep."
    )
    events_text = (
        "\n".join(
            f"- {ev['event_type']} at {ev.get('node_name', 'unknown')} (severity {ev.get('severity')})"
            for ev in events
        )
        or "No active events."
    )
    user_prompt = (
        f"{prev_text}\n\nCurrent world-state summary:\n{current_encoder_summary}\n\n"
        f"Active events:\n{events_text}"
    )
    return call_llm(TEMPORAL_LAYER_PROMPT, user_prompt)


def _numeric_propagation_summary(graph: nx.DiGraph) -> str:
    """Deterministic pre-computation of propagation pressure for the spatial LLM."""
    lines = []
    for source, target, attrs in graph.edges(data=True):
        multiplier = EDGE_MULTIPLIERS.get(attrs["edge_type"], 0.3)
        factor = attrs["weight"] * multiplier
        source_risk = (graph.nodes[source].get("flood_risk") or 0) + (
            graph.nodes[source].get("wildfire_smoke_risk") or 0
        )
        transfer = source_risk * factor
        if abs(transfer) > 0.05:
            verb = "amplifies risk into" if factor > 0 else "buffers"
            lines.append(
                f"{graph.nodes[source]['name']} {verb} {graph.nodes[target]['name']} "
                f"via {attrs['edge_type']} (transfer {transfer:.2f})"
            )
    lines.sort()
    return "\n".join(lines[:25]) or "No significant propagation pressure yet."


def spatial_layer(graph: nx.DiGraph, temporal_state: str) -> str:
    """Reason about propagation across graph edges."""
    adjacency = build_adjacency_list(graph)
    numeric_summary = _numeric_propagation_summary(graph)
    adjacency_text = json.dumps(
        {k: v for k, v in list(adjacency.items())[:12]}, indent=None
    )
    user_prompt = (
        f"Temporal state:\n{temporal_state}\n\n"
        f"Numeric propagation pre-computation (new_risk[target] += source_risk * weight * multiplier):\n"
        f"{numeric_summary}\n\n"
        f"Adjacency list (partial):\n{adjacency_text}"
    )
    return call_llm(SPATIAL_LAYER_PROMPT, user_prompt)


SHOCK_TEMPLATES = [
    ("localized_flash_flood", "flood_risk", "High rainfall and runoff raise localized flood risk."),
    ("wind_storm", "wind_speed_kmh", "Falling pressure and corridor winds could spawn a wind storm."),
    ("wildfire_smoke", "wildfire_smoke_risk", "Dry interior conditions could push smoke along wind corridors."),
    ("urban_heat_spike", "temperature_c", "Urban heat islands could concentrate a sudden heat spike."),
    ("cold_snap", "temperature_c", "An outflow pattern could pull cold alpine air into the corridor."),
    ("microclimate_anomaly", "disruption_score", "A strange microclimate pocket could form and disrupt locally."),
]


def stochastic_layer(graph: nx.DiGraph, temporal_state: str, spatial_state: str, chaos_level: float) -> dict:
    """Sample plausible uncertain shocks deterministically, with optional LLM explanation."""
    rng = random.Random(hash((round(chaos_level, 2), graph.number_of_nodes(), temporal_state, spatial_state)))

    trigger_probability = 0.25 + 0.65 * chaos_level
    if rng.random() > trigger_probability:
        return {
            "shock_type": "none",
            "target_node": None,
            "probability": round(1 - trigger_probability, 2),
            "severity": 0.0,
            "explanation": "No stochastic shock this timestep; the system stays on its current trajectory.",
        }

    risky_nodes = sorted(
        graph.nodes(data=True),
        key=lambda item: (item[1].get("flood_risk") or 0)
        + (item[1].get("wildfire_smoke_risk") or 0)
        + (item[1].get("disruption_score") or 0) / 100.0,
        reverse=True,
    )
    top_pool = risky_nodes[: max(3, int(3 + chaos_level * 7))]
    target_id, target_attrs = rng.choice(top_pool)
    shock_type, _, base_explanation = rng.choice(SHOCK_TEMPLATES)

    shock = {
        "shock_type": shock_type,
        "target_node": target_attrs["name"],
        "target_node_id": target_id,
        "probability": round(min(1.0, 0.15 + 0.5 * chaos_level + rng.uniform(0, 0.15)), 2),
        "severity": round(min(1.0, 0.3 + 0.55 * chaos_level + rng.uniform(0, 0.1)), 2),
        "explanation": base_explanation,
    }

    user_prompt = (
        f"Temporal state:\n{temporal_state}\n\nSpatial state:\n{spatial_state}\n\n"
        f"Chaos level: {chaos_level}\n"
        f"Deterministically sampled shock (keep type/target/probability/severity, improve explanation):\n"
        f"{json.dumps(shock)}"
    )
    llm_text = call_llm(STOCHASTIC_LAYER_PROMPT, user_prompt)
    try:
        parsed = json.loads(llm_text[llm_text.index("{") : llm_text.rindex("}") + 1])
        if isinstance(parsed.get("explanation"), str) and parsed["explanation"]:
            shock["explanation"] = parsed["explanation"]
    except (ValueError, KeyError):
        pass
    return shock
