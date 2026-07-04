"""Chaos Weather Dreamer - Streamlit UI."""

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import db
import seed_data
from demo_scenarios import EVENT_TYPES, SCENARIOS, get_scenario
from graph_engine import load_graph
from llm_client import llm_is_live
from simulation import build_final_story, run_simulation

st.set_page_config(page_title="Chaos Weather Dreamer", layout="wide")

METRICS = ["flood_risk", "wildfire_smoke_risk", "disruption_score", "mood_score"]


def ensure_db():
    if not os.path.exists(db.DB_PATH):
        seed_data.seed()


def plot_graph(timestep: int, metric: str):
    graph = load_graph(timestep)
    edge_traces = []
    for source, target, attrs in graph.edges(data=True):
        s, t = graph.nodes[source], graph.nodes[target]
        edge_traces.append(
            go.Scattergeo(
                lon=[s["longitude"], t["longitude"]],
                lat=[s["latitude"], t["latitude"]],
                mode="lines",
                line=dict(width=max(0.5, attrs["weight"] * 3), color="rgba(120,120,160,0.45)"),
                hoverinfo="text",
                text=f"{s['name']} → {t['name']} ({attrs['edge_type']}, w={attrs['weight']})",
                showlegend=False,
            )
        )

    lons, lats, values, texts = [], [], [], []
    for _, attrs in graph.nodes(data=True):
        lons.append(attrs["longitude"])
        lats.append(attrs["latitude"])
        val = attrs.get(metric) or 0
        values.append(val)
        texts.append(
            f"<b>{attrs['name']}</b><br>{metric}: {val}<br>"
            f"temp: {attrs.get('temperature_c')}C, rain: {attrs.get('rainfall_mm')}mm<br>"
            f"flood: {attrs.get('flood_risk')}, smoke: {attrs.get('wildfire_smoke_risk')}<br>"
            f"disruption: {attrs.get('disruption_score')}, mood: {attrs.get('mood_score')}"
        )

    colorscale = "RdYlGn" if metric == "mood_score" else "YlOrRd"
    node_trace = go.Scattergeo(
        lon=lons,
        lat=lats,
        mode="markers+text",
        text=[graph.nodes[n]["name"] for n in graph.nodes],
        textposition="top center",
        textfont=dict(size=8),
        hovertext=texts,
        hoverinfo="text",
        marker=dict(
            size=14,
            color=values,
            colorscale=colorscale,
            colorbar=dict(title=metric),
            line=dict(width=1, color="black"),
        ),
        showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        geo=dict(
            scope="north america",
            projection_type="mercator",
            lonaxis=dict(range=[-127.5, -118.0]),
            lataxis=dict(range=[47.0, 54.8]),
            showland=True,
            landcolor="rgb(235,235,225)",
            showlakes=True,
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        height=550,
    )
    return fig


def main():
    ensure_db()

    st.title("Chaos Weather Dreamer")
    st.caption("A Dreamer-inspired graph simulator for climate butterfly effects.")
    st.caption(
        "LLM mode: **live**" if llm_is_live() else "LLM mode: **mock fallback** (no API key detected)"
    )
    st.warning(
        "This is a creative hackathon simulation, not an official weather forecast "
        "or emergency alert system."
    )

    node_names = [n["name"] for n in db.get_nodes()]

    with st.sidebar:
        st.header("Controls")
        scenario_name = st.selectbox("Scenario", ["Custom"] + [s["name"] for s in SCENARIOS])
        scenario = get_scenario(scenario_name)

        start_node = st.selectbox(
            "Start node",
            node_names,
            index=node_names.index(scenario["start_node"]) if scenario else 0,
        )
        event_type = st.selectbox(
            "Event type",
            EVENT_TYPES,
            index=EVENT_TYPES.index(scenario["event_type"]) if scenario else 0,
        )
        severity = st.slider("Severity", 0.0, 1.0, scenario["severity"] if scenario else 0.7, 0.05)
        chaos_level = st.slider("Chaos level", 0.0, 1.0, 0.5, 0.05,
                                help="0.0 = realistic, 0.5 = dramatic, 1.0 = cursed")
        steps = st.slider("Timesteps", 1, 8, 5)

        run_clicked = st.button("Run Simulation", type="primary", use_container_width=True)
        if st.button("Reset DB", use_container_width=True):
            seed_data.seed()
            st.session_state.pop("results", None)
            st.session_state.pop("initial_event", None)
            st.success("Database reset and reseeded.")

    if run_clicked:
        db.clear_simulation_state()
        initial_event = {
            "start_node": start_node,
            "event_type": event_type,
            "severity": severity,
            "description": scenario["description"] if scenario else f"{event_type} begins in {start_node}.",
        }
        progress = st.progress(0.0, text="Simulating...")

        def on_progress(done, total):
            progress.progress(done / total, text=f"Simulating timestep {done + 1}/{total}...")

        results = run_simulation(initial_event, steps=steps, chaos_level=chaos_level,
                                 progress_callback=on_progress)
        progress.progress(1.0, text="Done.")
        st.session_state["results"] = results
        st.session_state["initial_event"] = initial_event

    st.subheader("World Graph")
    max_t = db.get_max_timestep()
    col1, col2 = st.columns([1, 1])
    with col1:
        metric = st.selectbox("Node color metric", METRICS, index=2)
    with col2:
        view_t = st.slider("View timestep", 0, max(1, max_t), min(max_t, 0)) if max_t > 0 else 0
    st.plotly_chart(plot_graph(view_t, metric), use_container_width=True)

    with st.expander("Node feature table"):
        feats = db.get_features(view_t)
        if feats:
            df = pd.DataFrame(feats).drop(columns=["id"])
            names = {n["node_id"]: n["name"] for n in db.get_nodes()}
            df.insert(0, "name", df["node_id"].map(names))
            st.dataframe(df, use_container_width=True, height=300)

    results = st.session_state.get("results")
    if results:
        st.subheader("Timestep Viewer")
        for res in results:
            with st.expander(f"Timestep {res['timestep']}", expanded=(res is results[-1])):
                if res["events"]:
                    st.markdown("**Active events**")
                    for ev in res["events"]:
                        st.markdown(
                            f"- `{ev['event_type']}` at **{ev.get('node_name', '?')}** "
                            f"(severity {ev.get('severity', 0):.2f}) — {ev.get('description', '')}"
                        )
                st.markdown("**Encoder summary**")
                st.info(res["encoder_summary"])
                st.markdown("**Temporal state**")
                st.write(res["temporal_state"])
                st.markdown("**Spatial state**")
                st.write(res["spatial_state"])
                st.markdown("**Stochastic shock**")
                st.json(res["shock"])
                if res.get("adjustment_log"):
                    st.markdown("**LLM adjustment layer**")
                    for node_name, entry in res["adjustment_log"].items():
                        st.markdown(f"- **{node_name}**: {entry}")
                st.markdown("**Decoder narrative**")
                st.success(res["narrative"])
                st.markdown("**Top 5 changed nodes**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"node": n["name"], "change_score": n["change_score"],
                             "changes": json.dumps(n["changes"])}
                            for n in res["top_changed_nodes"]
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        st.subheader("The Butterfly Effect")
        st.markdown(
            "\n\n".join(
                build_final_story(results, st.session_state["initial_event"]).split("\n")
            )
        )
    else:
        st.info("Pick a scenario in the sidebar and click **Run Simulation** to watch chaos unfold.")


if __name__ == "__main__":
    main()
