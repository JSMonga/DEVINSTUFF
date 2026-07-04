"""Seed the Chaos Weather Dreamer database with 30 BC/Vancouver-area nodes."""

import os
import random

import db

# name, region, lat, lon, elevation_m, description
NODES = [
    ("Vancouver Downtown", "Metro Vancouver", 49.2827, -123.1207, 20, "Dense urban core, high connectivity hub"),
    ("UBC", "Metro Vancouver", 49.2606, -123.2460, 85, "University peninsula surrounded by forest and ocean"),
    ("Kitsilano", "Metro Vancouver", 49.2684, -123.1554, 15, "Beachside residential neighbourhood"),
    ("Richmond", "Metro Vancouver", 49.1666, -123.1336, 1, "Low-lying delta city, flood-prone"),
    ("Burnaby", "Metro Vancouver", 49.2488, -122.9805, 130, "Suburban city with urban heat pockets"),
    ("Surrey", "Metro Vancouver", 49.1913, -122.8490, 75, "Large fast-growing suburban city"),
    ("North Vancouver", "Metro Vancouver", 49.3200, -123.0724, 100, "Mountain-backed city with heavy rainfall"),
    ("West Vancouver", "Metro Vancouver", 49.3286, -123.1602, 150, "Coastal slopes below mountains"),
    ("Coquitlam", "Metro Vancouver", 49.2838, -122.7932, 140, "Inland suburb near mountains and rivers"),
    ("New Westminster", "Metro Vancouver", 49.2057, -122.9110, 30, "Historic riverside city on the Fraser"),
    ("Delta", "Metro Vancouver", 49.0847, -123.0587, 5, "Flat farmland delta near the ocean"),
    ("Tsawwassen", "Metro Vancouver", 49.0136, -123.0836, 10, "Ferry terminal peninsula community"),
    ("Langley", "Fraser Valley", 49.1044, -122.6603, 85, "Suburban and agricultural mix"),
    ("Abbotsford", "Fraser Valley", 49.0504, -122.3045, 60, "Agricultural valley city, flood-exposed"),
    ("Chilliwack", "Fraser Valley", 49.1579, -121.9515, 30, "Fraser Valley farm city between mountains"),
    ("Squamish", "Sea to Sky", 49.7016, -123.1558, 60, "Windy town at the head of Howe Sound"),
    ("Whistler", "Sea to Sky", 50.1163, -122.9574, 670, "Alpine resort town, cold and snowy"),
    ("Hope", "Fraser Canyon", 49.3830, -121.4419, 40, "Gateway town where valley meets canyon"),
    ("Pemberton", "Sea to Sky", 50.3200, -122.8100, 210, "Farming valley north of Whistler"),
    ("Bowen Island", "Howe Sound", 49.3800, -123.3364, 50, "Forested island community in Howe Sound"),
    ("Nanaimo", "Vancouver Island", 49.1659, -123.9401, 20, "Island harbour city across the strait"),
    ("Victoria", "Vancouver Island", 48.4284, -123.3656, 20, "Provincial capital in a rain shadow"),
    ("Kelowna", "Okanagan", 49.8880, -119.4960, 340, "Dry interior lake city, wildfire-prone"),
    ("Kamloops", "Thompson", 50.6745, -120.3273, 345, "Hot dry interior crossroads city"),
    ("Merritt", "Nicola", 50.1113, -120.7862, 600, "Ranching town in dry grasslands"),
    ("Lytton", "Fraser Canyon", 50.2316, -121.5824, 170, "Canyon village, extreme heat and fire risk"),
    ("Prince George", "Northern BC", 53.9171, -122.7497, 575, "Northern hub city among forests"),
    ("Tofino", "Vancouver Island", 49.1530, -125.9066, 5, "Storm-battered open-Pacific coast town"),
    ("Parksville", "Vancouver Island", 49.3192, -124.3157, 10, "Mild east-island beach town"),
    ("Seattle", "Washington", 47.6062, -122.3321, 55, "Major US city to the south, linked by travel"),
]

# source_name, target_name, edge_type, weight, description
EDGES = [
    ("Vancouver Downtown", "Kitsilano", "proximity", 0.85, "Adjacent urban neighbourhoods"),
    ("Vancouver Downtown", "UBC", "coastal_influence", 0.72, "Shared coastal weather patterns"),
    ("Vancouver Downtown", "Burnaby", "urban_heat_island", 0.65, "Continuous built-up corridor"),
    ("Vancouver Downtown", "North Vancouver", "proximity", 0.70, "Across Burrard Inlet"),
    ("Vancouver Downtown", "Richmond", "commuter_flow", 0.60, "Canada Line commuter corridor"),
    ("Vancouver Downtown", "Surrey", "commuter_flow", 0.55, "Expo Line commuter corridor"),
    ("Vancouver Downtown", "Seattle", "commuter_flow", 0.35, "Cross-border travel corridor"),
    ("Kitsilano", "UBC", "proximity", 0.75, "Westside neighbours"),
    ("UBC", "Richmond", "coastal_influence", 0.50, "Shared Georgia Strait exposure"),
    ("Richmond", "Delta", "river_basin", 0.80, "Fraser delta lowlands"),
    ("Richmond", "New Westminster", "river_basin", 0.70, "Fraser River shoreline"),
    ("Delta", "Tsawwassen", "proximity", 0.85, "Same lowland peninsula"),
    ("Delta", "Surrey", "proximity", 0.65, "Adjacent municipalities"),
    ("Burnaby", "Coquitlam", "proximity", 0.75, "Adjacent suburbs"),
    ("Burnaby", "New Westminster", "urban_heat_island", 0.70, "Dense connected corridor"),
    ("New Westminster", "Surrey", "river_basin", 0.75, "Fraser crossing communities"),
    ("Surrey", "Langley", "proximity", 0.75, "Adjacent growing suburbs"),
    ("Langley", "Abbotsford", "proximity", 0.70, "Fraser Valley neighbours"),
    ("Abbotsford", "Chilliwack", "river_basin", 0.80, "Shared Fraser floodplain"),
    ("Chilliwack", "Hope", "river_basin", 0.75, "Upper valley floodplain"),
    ("Hope", "Lytton", "wind_corridor", 0.70, "Fraser Canyon wind funnel"),
    ("Lytton", "Kamloops", "weather_causal", 0.60, "Interior dry-belt heat sharing"),
    ("Lytton", "Merritt", "wind_corridor", 0.65, "Canyon-to-grassland air flow"),
    ("Merritt", "Kamloops", "proximity", 0.65, "Interior plateau neighbours"),
    ("Kamloops", "Kelowna", "weather_causal", 0.55, "Shared interior heat and smoke"),
    ("Kelowna", "Merritt", "wind_corridor", 0.50, "Okanagan-Nicola air exchange"),
    ("Kamloops", "Prince George", "weather_causal", 0.40, "Interior air mass movement"),
    ("North Vancouver", "West Vancouver", "proximity", 0.85, "North Shore neighbours"),
    ("North Vancouver", "Coquitlam", "mountain_barrier", 0.40, "Separated by mountain ridges"),
    ("West Vancouver", "Bowen Island", "coastal_influence", 0.65, "Howe Sound coastal weather"),
    ("West Vancouver", "Squamish", "wind_corridor", 0.70, "Howe Sound outflow winds"),
    ("Squamish", "Whistler", "wind_corridor", 0.75, "Sea to Sky corridor"),
    ("Whistler", "Pemberton", "proximity", 0.75, "Neighbouring valley towns"),
    ("Squamish", "Bowen Island", "coastal_influence", 0.60, "Howe Sound weather sharing"),
    ("Whistler", "North Vancouver", "mountain_barrier", 0.30, "Coast Mountains between"),
    ("Nanaimo", "Vancouver Downtown", "coastal_influence", 0.50, "Across the Strait of Georgia"),
    ("Nanaimo", "Parksville", "proximity", 0.80, "East island neighbours"),
    ("Nanaimo", "Victoria", "proximity", 0.55, "Island highway corridor"),
    ("Victoria", "Seattle", "coastal_influence", 0.45, "Shared Salish Sea weather"),
    ("Tofino", "Parksville", "mountain_barrier", 0.35, "Island ranges between coasts"),
    ("Tofino", "Nanaimo", "weather_causal", 0.45, "Pacific storms crossing the island"),
    ("Victoria", "Tsawwassen", "coastal_influence", 0.55, "Ferry-linked coastal pair"),
    ("Seattle", "Surrey", "commuter_flow", 0.40, "Cross-border road corridor"),
    ("Hope", "Coquitlam", "river_basin", 0.55, "Fraser River downstream link"),
    ("Pemberton", "Lytton", "weather_causal", 0.35, "Interior transition zone"),
    ("Kelowna", "Hope", "wind_corridor", 0.45, "Coquihalla air corridor"),
    ("Prince George", "Whistler", "weather_causal", 0.25, "Northern air mass reach"),
    ("Abbotsford", "Surrey", "commuter_flow", 0.55, "Highway 1 commuter flow"),
    ("Coquitlam", "New Westminster", "proximity", 0.70, "Adjacent river cities"),
    ("Bowen Island", "Vancouver Downtown", "commuter_flow", 0.40, "Ferry commuters"),
]


def _initial_features(node: dict, rng: random.Random) -> dict:
    """Generate plausible synthetic climate features for a node at timestep 0."""
    lat, elev = node["latitude"], node["elevation_m"]
    interior = node["longitude"] > -122.0
    coastal = elev < 60 and not interior

    base_temp = 21.0 - (elev / 150.0) + (3.0 if interior else 0.0) - (lat - 49.0) * 0.8
    temperature_c = round(base_temp + rng.uniform(-1.5, 1.5), 1)
    rainfall_mm = round(max(0.0, (2.0 if coastal else 0.5) + rng.uniform(-0.5, 2.0) - (2.0 if interior else 0.0)), 1)
    humidity_pct = round(min(95, max(25, (70 if coastal else 45) + rng.uniform(-8, 8))), 1)
    wind_speed_kmh = round(max(2.0, 12.0 + rng.uniform(-6, 10)), 1)
    pressure_hpa = round(1013 + rng.uniform(-4, 4), 1)
    flood_risk = round(min(1.0, max(0.0, (0.15 if elev < 30 else 0.05) + rng.uniform(0, 0.05))), 2)
    smoke_risk = round(min(1.0, max(0.0, (0.20 if interior else 0.04) + rng.uniform(0, 0.05))), 2)
    disruption_score = round(rng.uniform(5, 15), 1)
    mood_score = round(rng.uniform(65, 85), 1)

    return {
        "node_id": node["node_id"],
        "temperature_c": temperature_c,
        "rainfall_mm": rainfall_mm,
        "humidity_pct": humidity_pct,
        "wind_speed_kmh": wind_speed_kmh,
        "pressure_hpa": pressure_hpa,
        "flood_risk": flood_risk,
        "wildfire_smoke_risk": smoke_risk,
        "disruption_score": disruption_score,
        "mood_score": mood_score,
    }


def seed(reset: bool = True) -> None:
    if reset and os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.init_db()
    rng = random.Random(42)

    with db.get_connection() as conn:
        for i, (name, region, lat, lon, elev, desc) in enumerate(NODES, start=1):
            conn.execute(
                """INSERT INTO nodes (node_id, name, region, node_type, latitude, longitude, elevation_m, description)
                   VALUES (?, ?, ?, 'location', ?, ?, ?, ?)""",
                (i, name, region, lat, lon, elev, desc),
            )
        name_to_id = {name: i for i, (name, *_rest) in enumerate(NODES, start=1)}
        for src, tgt, etype, weight, desc in EDGES:
            conn.execute(
                "INSERT INTO edges (source_id, target_id, edge_type, weight, description) VALUES (?, ?, ?, ?, ?)",
                (name_to_id[src], name_to_id[tgt], etype, weight, desc),
            )

    features = [_initial_features(node, rng) for node in db.get_nodes()]
    db.save_features(0, features)
    print(f"Seeded {len(NODES)} nodes, {len(EDGES)} edges, {len(features)} feature rows at {db.DB_PATH}")


if __name__ == "__main__":
    seed()
