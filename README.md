# Chaos Weather Dreamer

A Dreamer-inspired graph world model where the world is a graph of climate/location nodes around Vancouver, BC. Each timestep, LLM-powered modules encode the graph, update a latent world state through temporal, spatial, and stochastic reasoning, and decode the next likely world state plus a butterfly-effect narrative.

> This is a hackathon prototype. It is not a scientific weather model. It is a creative, graph-based AI simulation showing how small climate events can cascade through a connected world.

## Why Dreamer-inspired?

Dreamer-style world models learn a latent state and roll it forward with a recurrent stochastic state-space model (RSSM). We mimic that shape with LLM layers:

- **Encoder** (2 layers): deterministic graph→text dump, then LLM compression into a world-state summary
- **RSSM-inspired core** (3 layers): temporal reasoning (what changed?), spatial reasoning (how do effects propagate through edges?), stochastic reasoning (what uncertain shock could hit next?)
- **Decoder**: turns the latent state into next-step node features, new events, and a human-readable butterfly-effect narrative

The simulation is **LLM-powered and stochastic**: numeric transition rules provide grounding, but the LLM steers the outcome — it decides which stochastic shocks fire (chosen from truly random candidate samples) and applies bounded feature adjustments on top of numeric propagation. Every run is different.

## Why a graph?

Butterfly effects need structure to travel through. Locations are nodes with climate features (temperature, rainfall, flood risk, smoke risk, disruption, mood), and typed weighted edges (proximity, river_basin, wind_corridor, mountain_barrier, commuter_flow, ...) define how shocks propagate — and where they're buffered.

## How to Run

```bash
pip install -r requirements.txt
cp .env.example .env      # add GOOGLE_API_KEY at deployment; falls back to mock offline
python seed_data.py       # creates data/chaos_weather.db with 30 BC nodes
streamlit run app.py
```

Then pick a scenario (e.g. **Rainfall Cascade**), set the chaos slider, and click **Run Simulation**.

## LLM Configuration

The app auto-detects a provider from the API keys present in the environment (checked in order): `GOOGLE_API_KEY`/`GEMINI_API_KEY` (Gemini, the primary provider), `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`. Override with `LLM_PROVIDER` and `LLM_MODEL` if needed.

With a live LLM:

- the **stochastic layer** samples random shock candidates each timestep and lets the LLM pick/reshape the shock (type, target, probability, severity) within validated bounds
- the **adjustment layer** lets the LLM nudge node features after numeric propagation, clamped per-feature so it can't break the simulation
- shocks and adjustments use an unseeded RNG, so **no two runs are identical**

If no key is set (or a call fails), the client falls back to mock responses so the demo still works offline — shocks and mock adjustments remain random. Set `MOCK_LLM=true` to force offline mode.

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
