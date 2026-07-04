"""Decoder: latent state -> next features, events, and butterfly-effect narrative."""

import json

import networkx as nx

from graph_engine import apply_events_and_propagate, top_changed_nodes
from llm_client import call_llm
from prompts import DECODER_PROMPT
from rssm import LatentState


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
    changed = top_changed_nodes(graph, next_features)

    user_prompt = (
        f"Chaos level: {chaos_level}\n\n"
        f"Temporal state:\n{latent_state.temporal_state}\n\n"
        f"Spatial state:\n{latent_state.spatial_state}\n\n"
        f"Stochastic shock:\n{json.dumps(shock)}\n\n"
        f"Numeric propagation results (deterministic simulator output):\n"
        f"{json.dumps(propagation_log)}\n\n"
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
    }
