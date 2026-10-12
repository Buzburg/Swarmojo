"""Autonomous Specialist Agent Instance for Swarmojo MetaHarness.

Binds an AgentManifest to an LLM model backend (local or remote), execution memory,
and tool triage via Fastgate.
"""
from __future__ import annotations

import json
import uuid
import hashlib
from app.control_store import ControlStore, digest
from app.engines.governance import HarnessGovernanceEngine
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.meta.manifest import AgentManifest
from app.meta.models import ModelClient, ModelConfig, ModelRegistry
from app.meta.environment import ExecutionEnvironment
from app.engines import (
    CompactKVManager,
    TitansMemory,
    extract_outer_json,
    repair_json_string,
    route_tools,
)


class MetaAgentInstance:
    """Live agent instance capable of reasoning, recalling memory, and executing actions."""

    def __init__(
        self,
        manifest: AgentManifest,
        model_client: Optional[ModelClient] = None,
        model_registry: Optional[ModelRegistry] = None,
        workspace_root: str = ".",
        run_id: Optional[str] = None,
        state_dir=None,
    ):
        self.manifest = manifest
        self.workspace_root = Path(workspace_root).resolve()
        self.registry = model_registry or ModelRegistry()
        self.client = model_client or ModelClient(registry=self.registry)

        # Resolve ModelConfig: override takes priority, then profile name
        if manifest.model_override:
            self.model_config = ModelConfig.from_dict(manifest.model_override)
        else:
            self.model_config = self.registry.get(manifest.model_profile)

        self.run_id = run_id or uuid.uuid4().hex
        self.scope = digest({'run_id': self.run_id, 'agent_id': manifest.id})
        self.store = ControlStore(self.workspace_root, state_dir)
        self.governance = HarnessGovernanceEngine(str(self.workspace_root), state_dir=state_dir)
        if manifest.id not in {r['id'] for r in self.governance.get_org_chart()['nodes']}:
            try:
                self.governance.hire_agent(manifest.id, manifest.name, manifest.role, model=self.model_config.model_id)
            except ValueError:
                if manifest.id not in {r['id'] for r in self.governance.get_org_chart()['nodes']}: raise
        memory_root = self.store.directory / 'memory' / hashlib.sha256(self.scope.encode()).hexdigest()
        memory_root.mkdir(parents=True, exist_ok=True)
        # Memory configuration
        if manifest.memory_policy == "titans":
            self.titans_mem: Optional[TitansMemory] = TitansMemory(root=str(memory_root))
            if not Path(self.titans_mem.meta_file).exists():
                self.titans_mem.init()
            self.compact_kv: Optional[CompactKVManager] = None
        elif manifest.memory_policy == "compact_kv":
            self.compact_kv = CompactKVManager(root=str(memory_root))
            if self.compact_kv.load() is None:
                self.compact_kv.init(f"Task for {manifest.name}")
            self.titans_mem = None
        else:
            self.titans_mem = None
            self.compact_kv = None

        self.history: List[Dict[str, str]] = []

    def build_system_prompt(self) -> str:
        """Compose system instructions with working memory preamble."""
        sections = [
            f"You are {self.manifest.name}, a specialist {self.manifest.role} in division [{self.manifest.division}].",
            f"Role Description: {self.manifest.description}",
        ]
        if self.manifest.system_prompt:
            sections.append(f"\nCore Directives:\n{self.manifest.system_prompt}")

        # Inject CompactKV scratchpad if active
        if self.compact_kv:
            preamble = self.compact_kv.generate_compact_preamble()
            if preamble:
                sections.append(f"\n{preamble}")

        if self.manifest.tools:
            sections.append(f"\nAvailable Capabilities: {', '.join(self.manifest.tools)}")

        return "\n\n".join(sections)

    def execute_turn(
        self,
        user_message: str,
        env: Optional[ExecutionEnvironment] = None,
        context_notes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a single agent reasoning and action turn."""
        # 1. Memory recall if using Titans
        recalled_notes: List[str] = []
        if self.titans_mem:
            recalled = self.titans_mem.read(user_message, top_k=3)
            for r in recalled:
                recalled_notes.append(f"[Titans Associative Memory: {r.get('key')}] {r.get('value')}")

        full_context = ""
        if context_notes or recalled_notes:
            all_notes = (context_notes or []) + recalled_notes
            full_context = "\n".join(f"- {n}" for n in all_notes)

        # 2. Build prompt messages
        messages = [{"role": "system", "content": self.build_system_prompt()}]
        for turn in self.history[-6:]:  # Keep recent history bounded
            messages.append(turn)

        user_content = user_message
        if full_context:
            user_content = f"{user_message}\n\nContext & Knowledge Notes:\n{full_context}"
        messages.append({"role": "user", "content": user_content})

        # 3. Tool triage if agent has tools and Fastgate is applicable
        retained_tools = self.manifest.tools
        if len(self.manifest.tools) > 4:
            routed = route_tools(user_message, self.manifest.tools, threshold=0.15)
            retained_tools = routed.get("retained_tools", self.manifest.tools)

        # 4. Invoke model backend
        cost = self.model_config.max_call_cost_usd
        if self.model_config.backend == 'mock': cost = 0.0
        if cost is None:
            raise ValueError('Configure max_call_cost_usd (0 for a free local provider) before inference')
        # Byte count is a tokenizer-independent conservative input reservation.
        token_bound = len(json.dumps(messages).encode()) + self.model_config.max_tokens
        request_id = uuid.uuid4().hex
        self.governance.reserve(self.manifest.id, token_bound, cost, request_id)
        try:
            res = self.client.generate(self.model_config, messages)
        except BaseException:
            self.governance.settle(request_id)  # Unknown remote effects retain their full reservation.
            raise
        usage = res.get('usage', {})
        measured = usage.get('total_tokens')
        if measured is None and 'prompt_tokens' in usage and 'completion_tokens' in usage:
            measured = usage['prompt_tokens'] + usage['completion_tokens']
        self.governance.settle(request_id, tokens=measured)
        reply_content = res.get("content", "")

        # 5. Extract JSON tool proposals if present
        json_block = extract_outer_json(reply_content)
        parsed_action = None
        if json_block:
            try:
                repaired = repair_json_string(json_block)
                parsed_action = json.loads(repaired)
            except Exception:
                pass

        # 6. Record verified facts into memory only through explicit execution receipts.
        # Model prose and recalled notes remain untrusted observations.

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": reply_content})

        return {
            "agent_id": self.manifest.id,
            "run_id": self.run_id,
            "scope": self.scope,
            "simulated": res.get("simulated", False),
            "usage": res.get("usage", {}),
            "agent_name": self.manifest.name,
            "role": self.manifest.role,
            "model": self.model_config.model_id,
            "backend": self.model_config.backend,
            "content": reply_content,
            "parsed_action": parsed_action,
            "tool_calls": res.get("tool_calls", []),
            "retained_tools": retained_tools,
            "latency_ms": res.get("latency_ms", 0.0),
        }


    def remember_receipt(self, receipt_id):
        content = self.store.record_fact(self.scope, receipt_id)
        if self.compact_kv:
            self.compact_kv.add_fact(content)
        if self.titans_mem:
            self.titans_mem.write(content, key=receipt_id)
        return {'receipt_id': receipt_id, 'scope': self.scope, 'verified': True}
