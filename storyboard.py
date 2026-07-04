"""Animated chronological playback and plain-language stage descriptions."""

import plotly.graph_objects as go

import db

GLOSSARY = {
    "Flood risk": "How likely an area is to flood, from 0 (safe) to 1 (almost certain flooding).",
    "Smoke risk": "How thick wildfire smoke is in the air, from 0 (clear air) to 1 (very smoky).",
    "Disruption score": "How much daily life is upset (closed roads, delays, cancellations), from 0 (normal day) to 100 (everything shut down).",
    "Mood score": "How people in the area are feeling overall, from 0 (miserable) to 100 (great).",
    "Severity": "How strong an event is, from 0 (barely noticeable) to 1 (as intense as it gets).",
    "Stochastic shock": "A surprise event added by chance — like real weather, the simulation rolls the dice each step.",
    "Timestep": "One 'tick' of simulated time. Each timestep, the weather spreads and changes.",
    "Ripple / propagation": "When trouble in one place spreads to connected places, like rings spreading in a pond.",
    "Butterfly effect": "The idea that one small event can snowball into big consequences elsewhere.",
    "Chaos level": "A dial for how wild the simulation is: 0 = realistic, 1 = anything goes.",
}

METRIC_LABELS = {
    "flood_risk": "flood risk",
    "wildfire_smoke_risk": "smoke risk",
    "disruption_score": "disruption",
    "mood_score": "mood",
}

_SHOCK_PHRASES = {
    "localized_flash_flood": "a sudden flash flood (a fast, unexpected burst of flooding)",
    "wildfire_smoke": "a plume of wildfire smoke drifting in",
    "microclimate_anomaly": "a microclimate anomaly (a small pocket of weirdly different local weather)",
    "heavy_rainfall": "an extra burst of heavy rain",
    "urban_heat_spike": "an urban heat spike (city surfaces trapping extra heat)",
    "infrastructure_failure": "an infrastructure failure (something like a road, pipe, or power line giving out)",
    "power_outage": "a power outage",
}

_EVENT_PHRASES = {
    "heavy_rainfall": "heavy rain pours down on",
    "urban_heat_spike": "a wave of trapped city heat builds up in",
    "wildfire_smoke": "wildfire smoke drifts over",
    "microclimate_anomaly": "strange local weather brews over",
    "localized_flash_flood": "a flash flood surges through",
    "infrastructure_failure": "key infrastructure breaks down in",
    "power_outage": "the power goes out in",
}


def _severity_word(sev: float) -> str:
    if sev >= 0.8:
        return "extreme"
    if sev >= 0.6:
        return "serious"
    if sev >= 0.4:
        return "moderate"
    return "mild"


def _event_phrase(event_type: str, node: str, severity: float) -> str:
    verb = _EVENT_PHRASES.get(event_type, f"{event_type.replace('_', ' ')} hits")
    return f"{verb} **{node}** ({_severity_word(severity)} — severity {severity:.2f})"


def plain_language_stage(res: dict) -> str:
    """One easy-to-understand paragraph describing what happens in a timestep."""
    parts = []
    events = res.get("events") or []
    if events:
        happening = "; ".join(
            _event_phrase(ev.get("event_type", "event"), ev.get("node_name") or "somewhere", float(ev.get("severity") or 0))
            for ev in events[:3]
        )
        parts.append(f"**What's happening:** {happening}.")

    top = res.get("top_changed_nodes") or []
    if top:
        names = ", ".join(n["name"] for n in top[:3])
        worst = top[0]
        change_bits = []
        for feat, delta in list(worst.get("changes", {}).items())[:2]:
            label = METRIC_LABELS.get(feat, feat.replace("_", " "))
            direction = "goes up" if delta > 0 else "goes down"
            change_bits.append(f"{label} {direction} by {abs(delta):g}")
        detail = f" — in {worst['name']}, {' and '.join(change_bits)}" if change_bits else ""
        parts.append(
            f"**Where it spreads:** the effects ripple outward to {names}{detail}. "
            "(Places are connected — by rivers, wind paths, and commuter routes — so trouble travels.)"
        )

    shock = res.get("shock") or {}
    if shock.get("shock_type") not in (None, "none"):
        phrase = _SHOCK_PHRASES.get(shock["shock_type"], shock["shock_type"].replace("_", " "))
        parts.append(
            f"**Plot twist:** out of nowhere, {phrase} strikes **{shock.get('target_node', '?')}**. "
            "This is a random 'shock' — the simulation adds surprises, just like real weather does."
        )

    if res.get("adjustment_log"):
        parts.append(
            "**AI fine-tuning:** the AI looked at the big picture and nudged a few numbers "
            "(within safe limits) to reflect knock-on effects the basic math would miss."
        )

    if not parts:
        parts.append("A quiet moment — conditions hold steady while pressure builds under the surface.")
    return "\n\n".join(parts)


def _frame_data(features: list[dict], nodes_by_id: dict, metric: str):
    lons, lats, values, texts, names = [], [], [], [], []
    for feat in features:
        node = nodes_by_id.get(feat["node_id"])
        if not node:
            continue
        val = feat.get(metric) or 0
        lons.append(node["longitude"])
        lats.append(node["latitude"])
        values.append(val)
        names.append(node["name"])
        texts.append(
            f"<b>{node['name']}</b><br>{METRIC_LABELS.get(metric, metric)}: {val:g}<br>"
            f"rain: {feat.get('rainfall_mm')}mm, flood: {feat.get('flood_risk')}<br>"
            f"smoke: {feat.get('wildfire_smoke_risk')}, disruption: {feat.get('disruption_score')}"
        )
    return lons, lats, values, texts, names


def build_animation(features_by_timestep: dict, metric: str = "disruption_score") -> go.Figure:
    """Plotly figure with play button: nodes morph smoothly between timesteps."""
    nodes_by_id = {n["node_id"]: n for n in db.get_nodes()}
    timesteps = sorted(features_by_timestep.keys())
    vmax = max(
        (feat.get(metric) or 0)
        for t in timesteps
        for feat in features_by_timestep[t]
    ) or 1

    colorscale = "RdYlGn" if metric == "mood_score" else "YlOrRd"

    edge_traces = []
    for edge in db.get_edges():
        s, t = nodes_by_id.get(edge["source_id"]), nodes_by_id.get(edge["target_id"])
        if not s or not t:
            continue
        edge_traces.append(
            go.Scattergeo(
                lon=[s["longitude"], t["longitude"]],
                lat=[s["latitude"], t["latitude"]],
                mode="lines",
                line=dict(width=max(0.5, edge["weight"] * 3), color="rgba(120,120,160,0.35)"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    def node_trace(t):
        lons, lats, values, texts, names = _frame_data(features_by_timestep[t], nodes_by_id, metric)
        return go.Scattergeo(
            lon=lons,
            lat=lats,
            mode="markers+text",
            text=names,
            textposition="top center",
            textfont=dict(size=8),
            hovertext=texts,
            hoverinfo="text",
            marker=dict(
                size=[10 + 14 * min(1.0, v / vmax) for v in values],
                color=values,
                cmin=0,
                cmax=vmax,
                colorscale=colorscale,
                colorbar=dict(title=METRIC_LABELS.get(metric, metric)),
                line=dict(width=1, color="black"),
            ),
            showlegend=False,
        )

    fig = go.Figure(data=edge_traces + [node_trace(timesteps[0])])
    fig.frames = [
        go.Frame(data=[node_trace(t)], name=str(t), traces=[len(edge_traces)])
        for t in timesteps
    ]

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
        margin=dict(l=0, r=0, t=30, b=0),
        height=550,
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                x=0.0,
                y=1.08,
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[None, dict(
                            frame=dict(duration=1500, redraw=True),
                            transition=dict(duration=900, easing="cubic-in-out"),
                            fromcurrent=True,
                        )],
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")],
                    ),
                ],
            )
        ],
        sliders=[
            dict(
                x=0.15,
                y=1.10,
                len=0.8,
                currentvalue=dict(prefix="Timestep ", font=dict(size=13)),
                steps=[
                    dict(
                        label=str(t),
                        method="animate",
                        args=[[str(t)], dict(
                            frame=dict(duration=600, redraw=True),
                            transition=dict(duration=400, easing="cubic-in-out"),
                            mode="immediate",
                        )],
                    )
                    for t in timesteps
                ],
            )
        ],
    )
    return fig
