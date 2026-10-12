"""Multi-model router and provider client for Swarmojo MetaHarness.

Supports:
- Local endpoints: Ollama, LM Studio, vLLM, Deep Reasoner, RWKV-7
- Generic OpenAI-compatible endpoints (local or remote)
- Deterministic mock execution for offline testing and bounded evaluations
- Heterogeneous model routing: different agents can use different local models
"""
from __future__ import annotations

import json
import os
import time
import math
import copy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import httpx


@dataclass
class ModelConfig:
    """Configuration for an LLM model backend."""
    model_id: str
    backend: str = "openai_compatible"  # "ollama", "lmstudio", "vllm", "rwkv", "openai_compatible", "mock"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "local"
    temperature: float = 0.2
    max_tokens: int = 2048
    context_window: int = 32768
    timeout_seconds: float = 60.0
    headers: Dict[str, str] = field(default_factory=dict)
    extra_params: Dict[str, Any] = field(default_factory=dict)
    max_call_cost_usd: Optional[float] = None
    supports_tools: bool = True

    def __post_init__(self):
        if not self.model_id or type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 131072:
            raise ValueError('Model ID and bounded output token limit are required')
        if not 0 < self.timeout_seconds <= 300 or not math.isfinite(self.timeout_seconds):
            raise ValueError('Model timeout must be finite and at most 300 seconds')
        if self.max_call_cost_usd is not None and (not math.isfinite(self.max_call_cost_usd) or self.max_call_cost_usd < 0):
            raise ValueError('Maximum call cost must be finite and nonnegative')
        if set(self.extra_params) & {'model', 'messages', 'tools', 'tool_choice', 'max_tokens', 'max_completion_tokens', 'stream'}:
            raise ValueError('Provider extras cannot override bounded request fields')

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModelConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Standard Default Model Profiles
DEFAULT_PROFILES: Dict[str, ModelConfig] = {
    "mock": ModelConfig(
        model_id="mock-deterministic",
        backend="mock",
        base_url="local://mock",
        temperature=0.0,
    ),
    "ollama-qwen-coder": ModelConfig(
        model_id="qwen2.5-coder:7b",
        backend="ollama",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    ),
    "ollama-deepseek-r1": ModelConfig(
        model_id="deepseek-r1:14b",
        backend="ollama",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    ),
    "ollama-llama3": ModelConfig(
        model_id="llama3.3:70b",
        backend="ollama",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    ),
    "lmstudio-local": ModelConfig(
        model_id="local-model",
        backend="lmstudio",
        base_url="http://localhost:1234/v1",
        api_key="lmstudio",
    ),
    "vllm-local": ModelConfig(
        model_id="default",
        backend="vllm",
        base_url="http://localhost:8000/v1",
        api_key="vllm",
    ),
    "deep-reasoner-local": ModelConfig(
        model_id="default",
        backend="openai_compatible",
        base_url="http://localhost:18084/v1",
        api_key="local",
    ),
    "rwkv-local": ModelConfig(
        model_id="rwkv7",
        backend="rwkv",
        base_url="http://localhost:8000/v1",
        api_key="rwkv",
    ),
}


class ModelRegistry:
    """Registry of available model configs for agents in the meta-harness."""

    def __init__(self):
        self._profiles: Dict[str, ModelConfig] = copy.deepcopy(DEFAULT_PROFILES)
        self._load_environment_overrides()

    def _load_environment_overrides(self) -> None:
        """Allow environment variables to configure default model backends."""
        default_url = os.environ.get("SWARMOJO_MODEL_URL") or os.environ.get("SWARMMOJO_LOCAL_LLM_URL")
        default_model = os.environ.get("SWARMOJO_MODEL_ID") or os.environ.get("SWARMMOJO_LOCAL_MODEL")
        if default_url and default_model:
            self._profiles["default-local"] = ModelConfig(
                model_id=default_model,
                backend="openai_compatible",
                base_url=default_url,
                api_key=os.environ.get("SWARMOJO_MODEL_API_KEY", os.environ.get("SWARMMOJO_LOCAL_API_KEY", "local")),
                max_call_cost_usd=float(os.environ['SWARMOJO_MAX_CALL_COST_USD']) if 'SWARMOJO_MAX_CALL_COST_USD' in os.environ else None,
            )

            self._profiles["default"] = self._profiles["default-local"]

    def register(self, profile_name: str, config: ModelConfig) -> None:
        self._profiles[profile_name] = config

    def get(self, profile_name: str) -> ModelConfig:
        if profile_name in self._profiles:
            return self._profiles[profile_name]
        raise ValueError(f"Unknown model profile: {profile_name}. Configure a provider or explicitly select mock.")

    def list_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {name: {**cfg.to_dict(), "api_key": "[redacted]", "headers": {k: "[redacted]" for k in cfg.headers}}
                for name, cfg in self._profiles.items()}


class ModelError(RuntimeError):
    """A provider failure is not a successful agent response."""


class ModelClient:
    """Executes completions across local or remote model backends with explicit failures."""

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or ModelRegistry()
        self.adapters = {}

    def register_adapter(self, backend, adapter):
        """Operator-supplied adapter(config, messages, tools) -> normalized completion."""
        if not backend or backend == 'mock' or not callable(adapter):
            raise ValueError('Expected a named provider adapter')
        self.adapters[backend] = adapter

    def generate(
        self,
        config: ModelConfig,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Synchronously generate a completion from the configured model backend."""
        start = time.perf_counter()

        if config.backend == "mock":
            return self._mock_completion(config, messages, start)

        if tools_schema and not config.supports_tools:
            raise ModelError('This provider profile does not support structured tools')
        try:
            if config.backend in self.adapters:
                result = self.adapters[config.backend](config, messages, tools_schema)
            elif config.backend in {'openai_compatible', 'ollama', 'lmstudio', 'vllm', 'rwkv'}:
                result = self._call_openai_compatible(config, messages, tools_schema, start)
            else:
                raise ModelError('No adapter registered for backend: ' + config.backend)
            if not isinstance(result, dict) or not isinstance(result.get('content'), str):
                raise ModelError('Provider returned an invalid completion')
            if len(result['content'].encode()) > 2_000_000:
                raise ModelError('Provider completion exceeded 2 MB')
            usage = result.get('usage', {})
            if not isinstance(usage, dict) or any(type(v) is not int or v < 0 for k, v in usage.items()
                                                 if k in {'prompt_tokens', 'completion_tokens', 'total_tokens'}):
                raise ModelError('Provider returned invalid usage')
            return {**result, 'backend': config.backend, 'model': config.model_id,
                    'simulated': False, 'latency_ms': round((time.perf_counter() - start) * 1000, 2)}
        except ModelError:
            raise
        except Exception as exc:
            raise ModelError('Provider request failed: ' + type(exc).__name__) from None

    def _call_openai_compatible(
        self,
        config: ModelConfig,
        messages: List[Dict[str, str]],
        tools_schema: Optional[List[Dict[str, Any]]],
        start_time: float,
    ) -> Dict[str, Any]:
        url = config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
            **config.headers,
        }
        payload: Dict[str, Any] = {
            "model": config.model_id,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            **config.extra_params,
        }
        if tools_schema:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"

        with httpx.Client(timeout=config.timeout_seconds) as client:
            with client.stream('POST', url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                body = bytearray()
                for chunk in resp.iter_bytes():
                    if len(body) + len(chunk) > 2_000_000:
                        raise ModelError('Provider response exceeded 2 MB')
                    if time.perf_counter() - start_time > config.timeout_seconds:
                        raise ModelError('Provider response exceeded its deadline')
                    body.extend(chunk)
                data = json.loads(body)

        choice = data["choices"][0]
        msg = choice.get("message", {})
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls", []),
            "model": config.model_id,
            "backend": config.backend,
            "latency_ms": round(latency_ms, 2),
            "usage": data.get("usage", {}),
            "finish_reason": choice.get("finish_reason", "stop"),
        }

    def _mock_completion(
        self,
        config: ModelConfig,
        messages: List[Dict[str, str]],
        start_time: float,
    ) -> Dict[str, Any]:
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        system_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")

        # Synthesize role-grounded answer based on system prompt and task
        content = f"[Response from {config.model_id}] Received task: {last_user[:160]}"
        if "Architect" in system_msg:
            content = f"### Architecture Plan\n1. Analyze requirements for: {last_user}\n2. Identify modular components and invariants.\n3. Execute changes through isolated sandbox."
        elif "Reviewer" in system_msg:
            content = "### Demonstration Review\nNo code inspection or test execution was performed."
        elif "Researcher" in system_msg:
            content = f"### Research Findings\n- Retrieved relevant knowledge and symbols for: {last_user}\n- Grounded context ready."
        elif "Coordinator" in system_msg:
            content = f"### Coordination Strategy\n1. Subtask A: Decomposed primary objective.\n2. Subtask B: Assigned to specialist agents.\n3. Synthesis: Ready for operator verification."

        content = "[SIMULATED] " + content
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "content": content,
            "tool_calls": [],
            "model": config.model_id,
            "backend": "mock",
            "simulated": True,
            "latency_ms": round(latency_ms, 2),
            "usage": {"prompt_tokens": len(last_user) // 4, "completion_tokens": len(content) // 4},
            "finish_reason": "stop",
        }
