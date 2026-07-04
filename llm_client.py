"""Provider-agnostic LLM wrapper with deterministic mock mode."""

import hashlib
import json
import os
import random

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODELS = {
    "gemini": "gemini-3.1-flash-lite",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "openrouter": "openai/gpt-4o-mini",
}

_KEY_ENV_VARS = {
    "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
}


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _provider() -> str:
    if os.getenv("MOCK_LLM", "false").lower() in ("1", "true", "yes"):
        return "mock"
    configured = os.getenv("LLM_PROVIDER", "").lower()
    if configured in ("google",):
        configured = "gemini"
    if configured:
        return configured
    for provider, env_vars in _KEY_ENV_VARS.items():
        if _first_env(*env_vars):
            return provider
    return "mock"


def llm_is_live() -> bool:
    """True when a real provider with an API key is active (not mock fallback)."""
    provider = _provider()
    return provider != "mock" and bool(_first_env(*_KEY_ENV_VARS.get(provider, ())))


def _mock_response(system_prompt: str, user_prompt: str) -> str:
    """Deterministic canned responses keyed on the system prompt role."""
    digest = hashlib.md5(user_prompt.encode()).hexdigest()[:6]
    sp = system_prompt.lower()
    if "compression layer" in sp:
        return (
            "- Coastal/urban cluster (Downtown, Kitsilano, UBC, Richmond) is mild and humid.\n"
            "- Interior nodes (Kamloops, Lytton, Kelowna) are hotter, drier, higher smoke risk.\n"
            "- Mountain nodes (Whistler, Pemberton) are cooler with precipitation exposure.\n"
            "- Vancouver Downtown is a high-connectivity hub; shocks there spread via "
            "commuter_flow and urban_heat_island edges.\n"
            f"- Low-lying delta nodes (Richmond, Delta) carry elevated baseline flood risk. [state {digest}]"
        )
    if "temporal layer" in sp:
        return (
            "Compared with the previous step, risk metrics rose at the event source node and "
            "its immediate neighbours, while distant nodes remain near baseline. Pressure is "
            "drifting downward around affected nodes, suggesting continued instability and "
            f"momentum toward further disruption next step. [state {digest}]"
        )
    if "spatial propagation layer" in sp:
        return (
            "Effects are propagating outward along the strongest outgoing edges: river_basin "
            "and wind_corridor links amplify transfer, proximity and commuter_flow edges carry "
            "moderate disruption, and mountain_barrier edges buffer nodes behind ridges. "
            f"High-connectivity hubs are the most exposed amplification points. [state {digest}]"
        )
    if "stochastic uncertainty layer" in sp:
        return (
            '{"shock_type": "pressure_drop_squall", "target_node": "Vancouver Downtown", '
            '"probability": 0.2, "severity": 0.5, '
            '"explanation": "Falling pressure over the coastal cluster could trigger a brief squall."}'
        )
    if "adjustment layer" in sp:
        rng = random.Random()
        features = ["disruption_score", "flood_risk", "wildfire_smoke_risk", "temperature_c", "mood_score"]
        adjustments = [
            {
                "node": "__random__",
                "feature": rng.choice(features),
                "delta": round(rng.uniform(-1.0, 1.0), 2),
                "reason": "Mock microvariation representing unresolved local dynamics.",
            }
            for _ in range(rng.randint(1, 3))
        ]
        return json.dumps({"adjustments": adjustments})
    if "decoder" in sp:
        return (
            "The initial disturbance nudged its node's features first, then leaked through the "
            "graph: strong edges carried risk into neighbouring communities, commuter flows "
            "translated weather stress into disruption, and buffered mountain nodes stayed "
            "calm. Each small change set up the next one — a classic butterfly cascade "
            f"across the region. [state {digest}]"
        )
    return f"Mock LLM response. [state {digest}]"


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    """Call configured LLM provider. Falls back to mock mode if no API key exists."""
    provider = _provider()
    model = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider, "")

    try:
        if provider == "gemini" and _first_env("GOOGLE_API_KEY", "GEMINI_API_KEY"):
            api_key = _first_env("GOOGLE_API_KEY", "GEMINI_API_KEY")
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": temperature},
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        if provider == "openai" and os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI

            client = OpenAI()
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content or ""

        if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            import anthropic

            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=model,
                max_tokens=1024,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")

        if provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
                json={
                    "model": model,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - demo stability: fall back to mock
        print(f"LLM call failed ({provider}): {exc}. Falling back to mock mode.")

    return _mock_response(system_prompt, user_prompt)
