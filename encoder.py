"""Encoder layers: deterministic graph-to-text plus LLM compression."""

import networkx as nx

from graph_engine import build_adjacency_list
from llm_client import call_llm
from prompts import ENCODER_LAYER_2_PROMPT


def encoder_layer_1(graph: nx.DiGraph, events: list[dict]) -> str:
    """Create faithful graph-to-text representation. No creative writing."""
    lines = []
    adjacency = build_adjacency_list(graph)
    for _, attrs in sorted(graph.nodes(data=True), key=lambda item: item[0]):
        name = attrs["name"]
        line = (
            f"{name}: temperature {attrs.get('temperature_c')}C, "
            f"rainfall {attrs.get('rainfall_mm')}mm, humidity {attrs.get('humidity_pct')}%, "
            f"wind {attrs.get('wind_speed_kmh')} km/h, pressure {attrs.get('pressure_hpa')} hPa, "
            f"flood risk {attrs.get('flood_risk')}, smoke risk {attrs.get('wildfire_smoke_risk')}, "
            f"disruption {attrs.get('disruption_score')}, mood {attrs.get('mood_score')}."
        )
        neighbors = adjacency.get(name, [])
        if neighbors:
            links = "; ".join(
                f"connects to {n['target']} via {n['edge_type']} (weight {n['weight']})"
                for n in neighbors
            )
            line += " " + links + "."
        lines.append(line)

    if events:
        lines.append("Active events:")
        for ev in events:
            lines.append(
                f"- {ev['event_type']} at {ev.get('node_name', 'unknown')} "
                f"(severity {ev.get('severity', 1.0)}): {ev.get('description', '')}"
            )
    else:
        lines.append("Active events: none.")
    return "\n".join(lines)


def encoder_layer_2(raw_graph_text: str) -> str:
    """Use LLM to compress raw graph facts into a structured world-state summary."""
    return call_llm(ENCODER_LAYER_2_PROMPT, raw_graph_text)
