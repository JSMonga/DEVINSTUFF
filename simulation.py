"""Simulation loop for Chaos Weather Dreamer."""

import json

import db
from decoder import decoder
from encoder import encoder_layer_1, encoder_layer_2
from graph_engine import load_graph
from rssm import LatentState, spatial_layer, stochastic_layer, temporal_layer


def insert_initial_event(initial_event: dict, timestep: int) -> None:
    node = db.get_node_by_name(initial_event["start_node"])
    db.insert_event(
        timestep,
        node["node_id"] if node else None,
        initial_event["event_type"],
        float(initial_event.get("severity", 0.7)),
        initial_event.get("description", ""),
    )


def run_simulation(initial_event: dict, start_timestep: int = 0, steps: int = 5, chaos_level: float = 0.5, progress_callback=None):
    """Run graph world model for N steps. Returns per-timestep results."""
    insert_initial_event(initial_event, start_timestep)
    prev_latent = None
    results = []

    for t in range(start_timestep, start_timestep + steps):
        if progress_callback:
            progress_callback(t - start_timestep, steps)

        graph = load_graph(t)
        events = db.get_events(t)

        raw_graph_text = encoder_layer_1(graph, events)
        encoder_summary = encoder_layer_2(raw_graph_text)

        temporal = temporal_layer(prev_latent, encoder_summary, events)
        spatial = spatial_layer(graph, temporal)
        shock = stochastic_layer(graph, temporal, spatial, chaos_level)

        latent = LatentState(t, temporal, spatial, shock)
        decoded = decoder(graph, latent, shock, chaos_level, events)

        db.save_latent_state(
            t, raw_graph_text, encoder_summary, temporal, spatial, shock, decoded["narrative"]
        )
        db.save_features(t + 1, decoded["next_features"])
        db.save_events(t + 1, decoded["new_events"])

        results.append(
            {
                "timestep": t,
                "events": events,
                "encoder_summary": encoder_summary,
                "temporal_state": temporal,
                "spatial_state": spatial,
                "shock": shock,
                "narrative": decoded["narrative"],
                "top_changed_nodes": decoded["top_changed_nodes"],
                "propagation_log": decoded["propagation_log"],
                "adjustment_log": decoded["adjustment_log"],
            }
        )
        prev_latent = latent

    return results


def build_final_story(results: list[dict], initial_event: dict) -> str:
    """Compose the final butterfly-effect story across all timesteps."""
    chain = [
        f"It started small: {initial_event['event_type'].replace('_', ' ')} at "
        f"{initial_event['start_node']} (severity {initial_event['severity']:.2f})."
    ]
    for res in results:
        top = res["top_changed_nodes"][:3]
        affected = ", ".join(n["name"] for n in top) if top else "nowhere in particular"
        shock = res["shock"]
        shock_text = (
            f" A stochastic {shock['shock_type'].replace('_', ' ')} then struck {shock['target_node']}."
            if shock.get("shock_type") not in (None, "none")
            else ""
        )
        chain.append(f"Timestep {res['timestep']}: ripples reached {affected}.{shock_text}")
    chain.append("Small causes, connected graph, big consequences — the butterfly effect, visualized.")
    return "\n".join(chain)


if __name__ == "__main__":
    import seed_data
    from demo_scenarios import SCENARIOS

    seed_data.seed()
    scenario = SCENARIOS[0]
    results = run_simulation(scenario, steps=3, chaos_level=0.5)
    for res in results:
        print(f"\n=== Timestep {res['timestep']} ===")
        print("Shock:", json.dumps(res["shock"]))
        print("Top changed:", [n["name"] for n in res["top_changed_nodes"]])
    print("\n" + build_final_story(results, scenario))
