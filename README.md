# Chaos Weather Dreamer

A Dreamer-inspired graph world model where the world is a graph of climate/location nodes around Vancouver, BC. Each timestep, LLM-powered modules encode the graph, update a latent world state through temporal, spatial, and stochastic reasoning, and decode the next likely world state plus a butterfly-effect narrative.

> This is a hackathon prototype. It is not a scientific weather model. It is a creative, graph-based AI simulation showing how small climate events can cascade through a connected world.

## Why Dreamer-inspired?

Dreamer-style world models learn a latent state and roll it forward with a recurrent stochastic state-space model (RSSM). We mimic that shape with LLM layers:

- **Encoder** (2 layers): deterministic graph→text dump, then LLM compression into a world-state summary
- **RSSM-inspired core** (3 layers): temporal reasoning (what changed?), spatial reasoning (how do effects propagate through edges?), stochastic reasoning (what uncertain shock could hit next?)
- **Decoder**: turns the latent state into next-step node features, new events, and a human-readable butterfly-effect narrative

The key idea: **the LLM is not the simulator**. The graph and deterministic numeric transition rules are the simulator. The LLM explains and compresses the evolving world state.

## Why a graph?

Butterfly effects need structure to travel through. Locations are nodes with climate features (temperature, rainfall, flood risk, smoke risk, disruption, mood), and typed weighted edges (proximity, river_basin, wind_corridor, mountain_barrier, commuter_flow, ...) define how shocks propagate — and where they're buffered.

## How to Run

```bash
pip install -r requirements.txt
cp .env.example .env      # mock mode works with no API keys
python seed_data.py       # creates data/chaos_weather.db with 30 BC nodes
streamlit run app.py
```

Then pick a scenario (e.g. **Rainfall Cascade**), set the chaos slider, and click **Run Simulation**.

## Mock Mode

Set in `.env`:

```text
MOCK_LLM=true
LLM_PROVIDER=mock
```

In mock mode, all LLM layers return deterministic canned responses, so the full demo works offline with no API key. The numeric simulation (event deltas, edge propagation, clamping) is always real and deterministic.

To use a real LLM, set `MOCK_LLM=false`, `LLM_PROVIDER=openai|anthropic|openrouter`, and the matching API key. If a call fails, the client automatically falls back to mock responses.

## Demo Script

> Most LLM demos just ask a model to write a story. We wanted the chaos to have structure.
>
> So we built a tiny Dreamer-inspired world model. The world is a graph: locations are nodes, climate relationships are edges, and weather features are stored in SQLite.
>
> First, the encoder turns the graph into an LLM-friendly world state. Then the RSSM-inspired core updates the latent state through temporal, spatial, and stochastic layers. Finally, the decoder predicts the next graph state and explains the butterfly effect.
>
> For example, a rainfall spike in North Vancouver does not just become a story. It changes node features, propagates through river basin and commuter-flow edges, raises risk in connected nodes, and then gets narrated.
>
> The LLM is not the world. The graph is the world. The LLM is the interface to the world model.

## Disclaimer

This is a creative hackathon simulation, not an official weather forecast or emergency alert system.
