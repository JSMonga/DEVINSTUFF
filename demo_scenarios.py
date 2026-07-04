"""Canned demo scenarios for Chaos Weather Dreamer."""

SCENARIOS = [
    {
        "name": "Rainfall Cascade",
        "start_node": "North Vancouver",
        "event_type": "heavy_rainfall",
        "severity": 0.75,
        "description": "Heavy rainfall begins near the mountains and tests the river/coastal graph.",
    },
    {
        "name": "Heat Island Spiral",
        "start_node": "Vancouver Downtown",
        "event_type": "urban_heat_spike",
        "severity": 0.70,
        "description": "A heat spike in downtown Vancouver spreads through urban and commuter edges.",
    },
    {
        "name": "Smoke Drift",
        "start_node": "Lytton",
        "event_type": "wildfire_smoke",
        "severity": 0.85,
        "description": "Wildfire smoke moves from the interior toward coastal population centers.",
    },
    {
        "name": "Maximum Chaos",
        "start_node": "UBC",
        "event_type": "microclimate_anomaly",
        "severity": 0.95,
        "description": "A tiny campus weather anomaly creates increasingly absurd but on-screen consequences.",
    },
]

EVENT_TYPES = [
    "heavy_rainfall",
    "urban_heat_spike",
    "wildfire_smoke",
    "microclimate_anomaly",
    "wind_storm",
    "cold_snap",
]


def get_scenario(name: str) -> dict | None:
    return next((s for s in SCENARIOS if s["name"] == name), None)
