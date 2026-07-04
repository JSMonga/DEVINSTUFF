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
from storyboard import GLOSSARY, build_animation, plain_language_stage

st.set_page_config(page_title="Chaos Weather Dreamer", layout="wide")

METRICS = ["flood_risk", "wildfire_smoke_risk", "disruption_score", "mood_score"]


def ensure_db():
    if not os.path.exists(db.DB_PATH):
        seed_data.seed()


def plot_graph(timestep: int, metric: str, features: list | None = None):
    graph = load_graph(0 if features is not None else timestep)
    if features is not None:
        by_id = {f["node_id"]: f for f in features}
        for node_id, attrs in graph.nodes(data=True):
            if node_id in by_id:
                attrs.update({k: v for k, v in by_id[node_id].items() if k not in ("id", "node_id", "timestep")})
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


def get_active_sim_id() -> int:
    sims = db.list_simulations()
    if not sims:
        sim_id = db.create_simulation(db.next_simulation_name())
        return sim_id
    active = st.session_state.get("active_sim")
    if active not in [s["sim_id"] for s in sims]:
        active = sims[-1]["sim_id"]
    return active


def simulation_menu():
    st.session_state.setdefault("menu_hidden", False)
    if st.session_state["menu_hidden"]:
        return
    col_new, col_hide = st.columns(2)
    with col_new:
        if st.button("\u2795 New", use_container_width=True, help="Create a new simulation"):
            st.session_state["active_sim"] = db.create_simulation(db.next_simulation_name())
            st.rerun()
    with col_hide:
        if st.button("\u25c0 Hide", use_container_width=True, help="Hide the simulation menu"):
            st.session_state["menu_hidden"] = True
            st.rerun()

    st.subheader("Simulations")
    active = st.session_state["active_sim"]
    for sim in db.list_simulations():
        is_active = sim["sim_id"] == active
        if st.button(
            sim["name"],
            key=f"sim_{sim['sim_id']}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["active_sim"] = sim["sim_id"]
            st.rerun()

    with st.expander("Rename simulation"):
        current = db.get_simulation(active)
        new_name = st.text_input("New name", value=current["name"] if current else "", key="rename_input")
        if st.button("Rename", use_container_width=True):
            if new_name.strip():
                db.rename_simulation(active, new_name.strip())
                st.rerun()
    st.divider()


def main():
    ensure_db()
    db.ensure_simulations_table()
    st.session_state["active_sim"] = get_active_sim_id()

    if st.session_state.get("menu_hidden"):
        _, right = st.columns([5, 1])
        with right:
            if st.button("\u2630 Show menu", use_container_width=True):
                st.session_state["menu_hidden"] = False
                st.rerun()

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
        simulation_menu()
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
            saved_sims = db.dump_simulations()
            seed_data.seed()
            db.restore_simulations(saved_sims)
            st.success("Database reset and reseeded (saved simulations kept).")

    active_sim_id = st.session_state["active_sim"]
    sim = db.get_simulation(active_sim_id)
    st.markdown(f"### \U0001f4c2 {sim['name']}" if sim else "")

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
        features_by_t = {t: db.get_features(t) for t in range(steps + 1)}
        db.save_simulation_run(active_sim_id, initial_event, chaos_level, steps, results, features_by_t)
        sim = db.get_simulation(active_sim_id)

    features_by_t = (sim or {}).get("features_by_timestep") or {}

    st.subheader("World Graph")
    max_t = max(features_by_t.keys()) if features_by_t else 0
    col1, col2 = st.columns([1, 1])
    with col1:
        metric = st.selectbox("Node color metric", METRICS, index=2)
    with col2:
        view_t = st.slider("View timestep", 0, max(1, max_t), min(max_t, 0)) if max_t > 0 else 0
    view_features = features_by_t.get(view_t)
    st.plotly_chart(plot_graph(view_t, metric, features=view_features), use_container_width=True)

    with st.expander("Node feature table"):
        feats = view_features if view_features is not None else db.get_features(view_t)
        if feats:
            df = pd.DataFrame(feats).drop(columns=["id"])
            names = {n["node_id"]: n["name"] for n in db.get_nodes()}
            df.insert(0, "name", df["node_id"].map(names))
            st.dataframe(df, use_container_width=True, height=300)

    results = (sim or {}).get("results")
    if results and features_by_t:
        st.subheader("Story Mode \u2014 watch it unfold")
        st.caption(
            "Press \u25b6 Play to watch the whole event chain develop chronologically \u2014 "
            "circles grow and turn red as places get hit harder, then the stages below explain "
            "each moment in plain language."
        )
        st.plotly_chart(build_animation(features_by_t, metric), use_container_width=True)

        for i, res in enumerate(results):
            st.markdown(f"#### Stage {i + 1} (Timestep {res['timestep']})")
            st.markdown(plain_language_stage(res))
        with st.expander("\U0001f4d6 What do these terms mean? (Plain-language glossary)"):
            for term, meaning in GLOSSARY.items():
                st.markdown(f"- **{term}**: {meaning}")

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
                build_final_story(results, sim["initial_event"]).split("\n")
            )
        )
    else:
        st.info("Pick a scenario in the sidebar and click **Run Simulation** to watch chaos unfold.")


if __name__ == "__main__":
    main()
