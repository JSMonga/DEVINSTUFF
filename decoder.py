"""Decoder: latent state -> next features, events, and butterfly-effect narrative."""

import json
import random

import networkx as nx

from graph_engine import apply_events_and_propagate, apply_llm_adjustments, top_changed_nodes
from llm_client import call_llm
from prompts import ADJUSTMENT_LAYER_PROMPT, DECODER_PROMPT
from rssm import LatentState


def _llm_adjustment_pass(
    graph: nx.DiGraph, next_features: list[dict], propagation_log: dict, chaos_level: float
) -> dict:
    """Ask the LLM for bounded feature nudges and apply them."""
    node_names = [attrs["name"] for _, attrs in graph.nodes(data=True)]
    sample = [f for f in next_features if f.get("disruption_score") is not None][:30]
    user_prompt = (
        f"Chaos level: {chaos_level}\n\n"
        f"Node names: {json.dumps(node_names)}\n\n"
        f"Propagation log:\n{json.dumps(propagation_log)}\n\n"
        f"Post-propagation features:\n{json.dumps(sample)}\n\n"
        "Propose up to 5 small adjustments as strict JSON."
    )
    llm_text = call_llm(ADJUSTMENT_LAYER_PROMPT, user_prompt, temperature=0.4 + 0.5 * chaos_level)
    try:
        parsed = json.loads(llm_text[llm_text.index("{") : llm_text.rindex("}") + 1])
        adjustments = parsed.get("adjustments") or []
    except (ValueError, KeyError):
        return {}
    rng = random.Random()
    for adj in adjustments:
        if adj.get("node") == "__random__":
            adj["node"] = rng.choice(node_names)
    return apply_llm_adjustments(graph, next_features, adjustments, chaos_level)


def decoder(graph: nx.DiGraph, latent_state: LatentState, shock: dict, chaos_level: float, events: list[dict]) -> dict:
    """Predict next timestep features and generate narrative explanation."""
    active_events = list(events)
    new_events = []

    if shock and shock.get("shock_type") not in (None, "none"):
        shock_event = {
            "node_id": shock.get("target_node_id"),
            "event_type": shock["shock_type"],
            "severity": float(shock.get("severity", 0.5)),
            "description": shock.get("explanation", ""),
        }
        active_events.append({**shock_event, "node_name": shock.get("target_node")})
        new_events.append(shock_event)

    next_features, propagation_log = apply_events_and_propagate(graph, active_events)
    adjustment_log = _llm_adjustment_pass(graph, next_features, propagation_log, chaos_level)
    changed = top_changed_nodes(graph, next_features)

    user_prompt = (
        f"Chaos level: {chaos_level}\n\n"
        f"Temporal state:\n{latent_state.temporal_state}\n\n"
        f"Spatial state:\n{latent_state.spatial_state}\n\n"
        f"Stochastic shock:\n{json.dumps(shock)}\n\n"
        f"Numeric propagation results:\n{json.dumps(propagation_log)}\n\n"
        f"LLM adjustment layer nudges:\n{json.dumps(adjustment_log)}\n\n"
        f"Top changed nodes:\n{json.dumps(changed)}\n\n"
        "Write a short butterfly-effect narrative for this timestep."
    )
    narrative = call_llm(DECODER_PROMPT, user_prompt, temperature=0.4 + 0.4 * chaos_level)

    return {
        "next_features": next_features,
        "new_events": new_events,
        "narrative": narrative,
        "top_changed_nodes": changed,
        "propagation_log": propagation_log,
        "adjustment_log": adjustment_log,
    }
