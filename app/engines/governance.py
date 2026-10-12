"""Swarmojo Harness Governance & Organizational Control Engine.

Inspired by enterprise agent control planes (Paperclip, CrewAI Enterprise),
providing organizational hierarchy (Org Chart), budget enforcement, heartbeat
scheduling, goal/task issues with dependency blocking, and human-in-the-loop approvals.
"""
from __future__ import annotations

import json
import math
import uuid
from functools import wraps
from app.control_store import ControlStore, packed
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def durable(write=False):
    def decorate(method):
        @wraps(method)
        def wrapped(self, *args, **kwargs):
            with self.store.transaction() as db:
                self._restore(json.loads(db.execute("SELECT value FROM state WHERE name='governance'").fetchone()[0]))
                result = method(self, *args, **kwargs)
                if write:
                    db.execute("UPDATE state SET value=? WHERE name='governance'", (packed(self._state()),))
                return result
        return wrapped
    return decorate


def amount(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError('Budget amounts must be finite and nonnegative')
    return value


@dataclass
class AgentEmployee:
    id: str
    name: str
    role: str
    tier: str  # "executive", "lead", "specialist", "auditor"
    reports_to: Optional[str] = None
    model: str = "default"
    budget_cap_usd: float = 50.0
    current_spend_usd: float = 0.0
    token_cap: int = 2_000_000
    tokens_used: int = 0
    heartbeat_interval_sec: int = 60
    last_heartbeat: float = field(default_factory=time.time)
    status: str = "active"  # "active", "busy", "idle", "paused", "waiting_approval"
    avatar: str = "🤖"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskIssue:
    id: str
    title: str
    description: str
    assignee_id: str
    priority: str = "medium"  # "critical", "high", "medium", "low"
    status: str = "backlog"   # "backlog", "in_progress", "blocked", "review", "done"
    blocked_by: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalItem:
    id: str
    action_type: str  # "git_push", "file_overwrite", "api_spend", "external_deploy"
    requested_by: str
    description: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # "pending", "approved", "rejected"
    requested_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HarnessGovernanceEngine:
    """Manages multi-agent organizational structure, budgets, tasks, and approval gates."""

    def __init__(self, workspace_root: str = ".", *, state_dir=None, demo=False):
        self.workspace_root = Path(workspace_root).resolve()
        self.store = ControlStore(self.workspace_root, state_dir)
        self.storage_dir = self.store.directory

        self._employees: Dict[str, AgentEmployee] = {}
        self._tasks: Dict[str, TaskIssue] = {}
        self._approvals: Dict[str, ApprovalItem] = {}
        self._settings: Dict[str, Any] = {
            "heartbeat_interval_default": 60,
            "heartbeat_mode": "scheduled",  # "scheduled", "event_driven", "manual"
            "concurrency_mode": "statefresh_occ",  # "statefresh_occ", "strict_lock"
            "auto_rollback_on_failure": True,
            "cost_hard_cap_usd": 250.0,
            "require_human_approval_for_push": True,
            "require_human_approval_for_deploy": True,
            "byoa_connectors": {
                "claude_code": {"enabled": True, "endpoint": "http://localhost:5210/agent"},
                "opencode": {"enabled": True, "endpoint": "http://localhost:5211/agent"},
                "codex": {"enabled": True, "endpoint": "http://localhost:5212/agent"},
                "ollama_local": {"enabled": True, "endpoint": "http://localhost:11434/api"},
                "native_mojo": {"enabled": True, "speedup": "sub-10µs"},
            },
        }

        self._reservations = {}
        if demo:
            self._init_defaults()
        with self.store.transaction() as db:
            db.execute("INSERT OR IGNORE INTO state VALUES ('governance',?)", (packed(self._state()),))
            self._restore(json.loads(db.execute("SELECT value FROM state WHERE name='governance'").fetchone()[0]))

    def _state(self):
        return {'employees': {k: v.to_dict() for k, v in self._employees.items()},
                'tasks': {k: v.to_dict() for k, v in self._tasks.items()},
                'approvals': {k: v.to_dict() for k, v in self._approvals.items()},
                'settings': self._settings, 'reservations': self._reservations}

    def _restore(self, state):
        self._employees = {k: AgentEmployee(**v) for k, v in state['employees'].items()}
        self._tasks = {k: TaskIssue(**v) for k, v in state['tasks'].items()}
        self._approvals = {k: ApprovalItem(**v) for k, v in state['approvals'].items()}
        self._settings = state['settings']
        self._reservations = state.get('reservations', {})


    def _init_defaults(self) -> None:
        """Seed default corporate hierarchy and sample tasks/approvals."""
        # 1. Corporate Hierarchy
        default_employees = [
            AgentEmployee(
                id="atlas",
                name="Atlas",
                role="Swarm Coordinator & Executive Lead",
                tier="executive",
                reports_to=None,
                model="deepseek-r1",
                budget_cap_usd=80.0,
                current_spend_usd=14.20,
                token_cap=5_000_000,
                tokens_used=720_000,
                heartbeat_interval_sec=30,
                status="active",
                avatar="⚡",
            ),
            AgentEmployee(
                id="daedalus",
                name="Daedalus",
                role="Principal DeepCode Architect",
                tier="lead",
                reports_to="atlas",
                model="qwen-coder",
                budget_cap_usd=60.0,
                current_spend_usd=28.50,
                token_cap=4_000_000,
                tokens_used=1_850_000,
                heartbeat_interval_sec=45,
                status="busy",
                avatar="🛠️",
            ),
            AgentEmployee(
                id="vitruvius",
                name="Vitruvius",
                role="Staff UI/UX Systems Designer",
                tier="specialist",
                reports_to="daedalus",
                model="qwen-coder",
                budget_cap_usd=40.0,
                current_spend_usd=6.15,
                token_cap=2_000_000,
                tokens_used=310_000,
                heartbeat_interval_sec=60,
                status="idle",
                avatar="🎨",
            ),
            AgentEmployee(
                id="lumiere",
                name="Lumiere",
                role="Studio Director & Multimodal Producer",
                tier="specialist",
                reports_to="atlas",
                model="flux-dev",
                budget_cap_usd=50.0,
                current_spend_usd=19.40,
                token_cap=3_000_000,
                tokens_used=950_000,
                heartbeat_interval_sec=60,
                status="busy",
                avatar="🎬",
            ),
            AgentEmployee(
                id="orwell",
                name="Orwell",
                role="Lead Ghost Scribe & Technical Writer",
                tier="specialist",
                reports_to="atlas",
                model="qwen-coder",
                budget_cap_usd=30.0,
                current_spend_usd=4.80,
                token_cap=2_000_000,
                tokens_used=240_000,
                heartbeat_interval_sec=90,
                status="active",
                avatar="✍️",
            ),
            AgentEmployee(
                id="aegis",
                name="Aegis",
                role="Chief Security Auditor & Constitutional Guard",
                tier="auditor",
                reports_to="atlas",
                model="llama3",
                budget_cap_usd=40.0,
                current_spend_usd=5.20,
                token_cap=2_000_000,
                tokens_used=260_000,
                heartbeat_interval_sec=15,
                status="active",
                avatar="🛡️",
            ),
        ]
        for emp in default_employees:
            self._employees[emp.id] = emp

        # 2. Sample Goal & Task Issues
        default_tasks = [
            TaskIssue(
                id="TASK-101",
                title="Swarmojo HUD Hive UI Unification",
                description="Align HUD themes and brand tokens with official Buzburg honey gold and charcoal.",
                assignee_id="vitruvius",
                priority="high",
                status="done",
            ),
            TaskIssue(
                id="TASK-102",
                title="Sub-10µs In-Memory Symdex Cache Warmup",
                description="Preload syntax graph for fastgate triage in native Mojo kernel.",
                assignee_id="daedalus",
                priority="critical",
                status="in_progress",
            ),
            TaskIssue(
                id="TASK-103",
                title="Audit Path Traversal on Windows Reserved Devices",
                description="Run PathSentry checks on COM1, LPT1, and AUX device names.",
                assignee_id="aegis",
                priority="high",
                status="in_progress",
            ),
            TaskIssue(
                id="TASK-104",
                title="4K 16:9 Production Studio Banner Reel",
                description="Render diffusion graph keyframes for multimodal release assets.",
                assignee_id="lumiere",
                priority="medium",
                status="review",
            ),
            TaskIssue(
                id="TASK-105",
                title="Ghost Protocol Cadence Polish",
                description="Audit marketing docs for banned AI jargon and ensure sentence cadence variance > 7.0.",
                assignee_id="orwell",
                priority="medium",
                status="backlog",
            ),
            TaskIssue(
                id="TASK-106",
                title="StateFresh Distributed File Lease OCC Lock",
                description="Implement optimistic lock checks across parallel worker forks.",
                assignee_id="daedalus",
                priority="critical",
                status="blocked",
                blocked_by=["TASK-102"],
            ),
        ]
        for t in default_tasks:
            self._tasks[t.id] = t

        # 3. Sample Human Approval Items
        default_approvals = [
            ApprovalItem(
                id="APPR-401",
                action_type="git_push",
                requested_by="daedalus",
                description="Push release commits directly to origin/main (Buzburg/Swarmojo)",
                payload={"branch": "main", "commits_count": 3, "verified_by": "WorkflowProof"},
                status="pending",
            ),
            ApprovalItem(
                id="APPR-402",
                action_type="api_spend",
                requested_by="lumiere",
                description="Allocate $15.00 GPU cloud burst budget for 60-second video diffusion render",
                payload={"amount_usd": 15.0, "provider": "Flux-Dev-Cloud"},
                status="pending",
            ),
        ]
        for a in default_approvals:
            self._approvals[a.id] = a

    # Org Chart
    @durable()
    def get_org_chart(self) -> Dict[str, Any]:
        """Returns organizational tree with reporting relationships and budget statistics."""
        nodes = []
        edges = []
        for emp in self._employees.values():
            nodes.append(emp.to_dict())
            if emp.reports_to:
                edges.append({"from": emp.reports_to, "to": emp.id})

        return {
            "total_headcount": len(self._employees),
            "nodes": nodes,
            "edges": edges,
        }

    @durable(write=True)
    def hire_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        tier: str = "specialist",
        reports_to: Optional[str] = None,
        model: str = "default",
        budget_cap_usd: float = 30.0,
        avatar: str = "🤖",
    ) -> Dict[str, Any]:
        """Hire/register a new autonomous agent into the company hierarchy."""
        if agent_id in self._employees:
            raise ValueError('Agent already registered; cannot reset spend by registering again')
        amount(budget_cap_usd)
        if reports_to and reports_to not in self._employees:
            raise ValueError('Unknown reporting agent')
        emp = AgentEmployee(
            id=agent_id,
            name=name,
            role=role,
            tier=tier,
            reports_to=reports_to,
            model=model,
            budget_cap_usd=budget_cap_usd,
            avatar=avatar,
        )
        self._employees[agent_id] = emp
        return {"status": "hired", "agent": emp.to_dict()}

    # Budget & Governance
    @durable()
    def get_budget_summary(self) -> Dict[str, Any]:
        """Calculates total spend vs caps and per-agent metrics."""
        total_spent = sum(e.current_spend_usd for e in self._employees.values())
        total_cap = sum(e.budget_cap_usd for e in self._employees.values())
        hard_cap = self._settings["cost_hard_cap_usd"]
        reserved = {k: v for k, v in self._reservations.items() if v["status"] == "reserved"}

        return {
            "total_spend_usd": round(total_spent, 2),
            "allocated_cap_usd": round(total_cap, 2),
            "reserved_cost_usd": sum(v["cost_usd"] for v in reserved.values()),
            "reservations": reserved,
            "organization_hard_cap_usd": round(hard_cap, 2),
            "budget_used_percentage": round((total_spent / max(hard_cap, 1.0)) * 100.0, 1),
            "agents_over_budget": [
                e.id for e in self._employees.values() if e.current_spend_usd >= e.budget_cap_usd
            ],
            "per_agent": [
                {
                    "id": e.id,
                    "name": e.name,
                    "spent": round(e.current_spend_usd, 2),
                    "cap": round(e.budget_cap_usd, 2),
                    "tokens": e.tokens_used,
                    "token_cap": e.token_cap,
                    "percent": round((e.current_spend_usd / max(e.budget_cap_usd, 1.0)) * 100.0, 1),
                }
                for e in self._employees.values()
            ],
        }

    # Heartbeat System
    @durable(write=True)
    def trigger_heartbeat(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Wakes up agents on demand or triggers the scheduled execution pulse."""
        now = time.time()
        woken = []
        target_ids = [agent_id] if agent_id and agent_id in self._employees else list(self._employees.keys())

        for aid in target_ids:
            emp = self._employees[aid]
            emp.last_heartbeat = now
            woken.append({
                "id": emp.id,
                "name": emp.name,
                "status": emp.status,
                "timestamp": now,
            })

        return {
            "status": "heartbeat_dispatched",
            "agents_woken_count": len(woken),
            "agents": woken,
            "next_interval_sec": self._settings["heartbeat_interval_default"],
        }

    # Task & Issue Tracking (Kanban)
    @durable()
    def list_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns issues organized by Kanban column."""
        columns: Dict[str, List[Dict[str, Any]]] = {
            "backlog": [],
            "in_progress": [],
            "blocked": [],
            "review": [],
            "done": [],
        }
        for t in self._tasks.values():
            st = t.status if t.status in columns else "backlog"
            columns[st].append(t.to_dict())
        return columns

    @durable(write=True)
    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        assignee_id: str = "atlas",
        priority: str = "medium",
        blocked_by: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Creates an issue and assigns it to an agent."""
        dependencies = blocked_by or []
        if task_id in self._tasks or task_id in dependencies:
            raise ValueError('Task IDs are unique and cannot depend on themselves')
        if not isinstance(dependencies, list) or any(x not in self._tasks for x in dependencies):
            raise ValueError('Dependencies must name existing tasks')
        if assignee_id not in self._employees:
            raise ValueError('Unknown task assignee')
        issue = TaskIssue(
            id=task_id,
            title=title,
            description=description,
            assignee_id=assignee_id,
            priority=priority,
            blocked_by=blocked_by or [],
        )
        self._tasks[task_id] = issue
        return {"status": "created", "task": issue.to_dict()}

    @durable(write=True)
    def update_task_details(self, task_id, title, description, assignee_id, priority, blocked_by):
        """Edit a task without bypassing dependency or status-transition checks."""
        if task_id not in self._tasks or assignee_id not in self._employees:
            raise ValueError('Unknown task or assignee')
        if any(id not in self._tasks for id in blocked_by):
            raise ValueError('Dependencies must name existing tasks')
        pending, visited = list(blocked_by), set()
        while pending:
            id = pending.pop()
            if id == task_id:
                raise ValueError('Task dependencies cannot form a cycle')
            if id not in visited:
                visited.add(id)
                pending.extend(self._tasks[id].blocked_by)
        task = self._tasks[task_id]
        if task.status in {'in_progress', 'review', 'done'} and any(
                self._tasks[id].status != 'done' for id in blocked_by):
            raise ValueError('Active tasks cannot gain unfinished dependencies; block the task first')
        task.title, task.description, task.assignee_id = title, description, assignee_id
        task.priority, task.blocked_by = priority, list(dict.fromkeys(blocked_by))
        task.updated_at = time.time()
        return {'status': 'updated', 'task': task.to_dict()}

    @durable(write=True)
    def update_task_status(self, task_id: str, new_status: str) -> Dict[str, Any]:
        """Moves a task across Kanban columns."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found.")
        task = self._tasks[task_id]
        transitions = {'backlog': {'in_progress', 'blocked'}, 'in_progress': {'review', 'blocked'},
                       'blocked': {'backlog', 'in_progress'}, 'review': {'done', 'in_progress'}, 'done': set()}
        if new_status not in transitions.get(task.status, set()):
            raise ValueError('Invalid task status transition')
        if new_status in {'in_progress', 'review', 'done'} and any(
                self._tasks[x].status != 'done' for x in task.blocked_by):
            raise ValueError('Task has unfinished dependencies')
        task.status = new_status
        task.updated_at = time.time()
        return {"status": "updated", "task": task.to_dict()}

    # Human Approval Queue
    @durable()
    def list_approvals(self, pending_only: bool = False) -> List[Dict[str, Any]]:
        """Returns approval gates for high-stakes actions."""
        res = []
        for a in self._approvals.values():
            if pending_only and a.status != "pending":
                continue
            res.append(a.to_dict())
        return res

    @durable(write=True)
    def resolve_approval(self, approval_id: str, action: str, approver: str = "HumanAdmin") -> Dict[str, Any]:
        """Approves or rejects a gated action."""
        if approval_id not in self._approvals:
            raise ValueError(f"Approval item {approval_id} not found.")
        item = self._approvals[approval_id]
        if action not in {'approve', 'reject'} or item.status != 'pending':
            raise ValueError('Only pending approvals can be explicitly approved or rejected')
        item.status = "approved" if action == "approve" else "rejected"
        item.resolved_at = time.time()
        item.resolved_by = approver
        return {"status": "resolved", "decision": item.status, "item": item.to_dict()}

    # Harness Options & BYOA Settings
    @durable()
    def get_settings(self) -> Dict[str, Any]:
        return json.loads(packed(self._settings))

    @durable(write=True)
    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(updates, dict) or not set(updates) <= set(self._settings):
            raise ValueError('Unknown governance settings')
        if 'cost_hard_cap_usd' in updates: amount(updates['cost_hard_cap_usd'])
        self._settings.update(updates)
        return {"status": "updated", "settings": self._settings}


    @durable(write=True)
    def reserve(self, agent_id, tokens, cost_usd, request_id):
        """Reserve the worst-case cost atomically before a provider is contacted."""
        amount(cost_usd)
        if type(tokens) is not int or tokens < 0:
            raise ValueError('Token reservation must be a nonnegative integer')
        if request_id in self._reservations:
            raise ValueError('Model request was already dispatched or reserved')
        agent = self._employees.get(agent_id)
        if not agent:
            raise ValueError('Agent must be registered before inference')
        held = [v for v in self._reservations.values() if v['status'] == 'reserved']
        own = [v for v in held if v['agent_id'] == agent_id]
        if (agent.current_spend_usd + sum(v['cost_usd'] for v in own) + cost_usd > agent.budget_cap_usd
                or agent.tokens_used + sum(v['tokens'] for v in own) + tokens > agent.token_cap
                or sum(a.current_spend_usd for a in self._employees.values())
                   + sum(v['cost_usd'] for v in held) + cost_usd > self._settings['cost_hard_cap_usd']):
            raise ValueError('Budget exhausted before provider dispatch')
        self._reservations[request_id] = {'agent_id': agent_id, 'tokens': tokens,
                                        'cost_usd': cost_usd, 'status': 'reserved'}
        return dict(self._reservations[request_id])

    @durable(write=True)
    def settle(self, request_id, tokens=None, cost_usd=None):
        """Unknown usage conservatively consumes the full reservation; never silently free it."""
        entry = self._reservations[request_id]
        if entry['status'] != 'reserved':
            raise ValueError('Model request already settled')
        tokens = entry['tokens'] if tokens is None else tokens
        cost_usd = entry['cost_usd'] if cost_usd is None else cost_usd
        amount(cost_usd)
        if type(tokens) is not int or tokens < 0:
            raise ValueError('Invalid measured token usage')
        agent = self._employees[entry['agent_id']]
        agent.tokens_used += tokens
        agent.current_spend_usd += cost_usd
        entry.update(status='settled', actual_tokens=tokens, actual_cost_usd=cost_usd)
        return dict(entry)
