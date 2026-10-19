"""FastMCP Tool Registrations for Swarmojo Specialized Engines.

Exposes Buzburg AI specialized engines as native FastMCP tools:
- Symdex: High-speed symbol & call-graph lookup (<20 µs)
- Titans: Test-time neural memory (arXiv:2501.00663)
- ToolCall: JSON extraction, auto-repair, and schema coercion
- Sieve: Streaming terminal and compiler log compaction
- Horizon: External task graph & anti-loop circuit breaker
- Fastgate: 256-dim phase-vector System-1 tool triage router
- CompactKV: VRAM-capped rolling structured scratchpad (<800 tokens)
- Rewind: Content-addressed workspace snapshotting and microsecond rollback
- PathCarry: Filename safety, cross-platform reserved-name & path audit
"""
from __future__ import annotations

from app.mcp_annotations import tool_annotations

import json
from pathlib import Path
from fastmcp import FastMCP

from app.engines import (
    SymdexIndex,
    TitansMemory,
    extract_outer_json,
    repair_json_string,
    compact_text,
    HorizonManager,
    route_tools,
    CompactKVManager,
    RewindEngine,
    audit_directory,
)


def register_engine_tools(server: FastMCP) -> None:
    @server.tool(annotations=tool_annotations('symnexus_query'))
    def symnexus_query(symbol: str, query_type: str = "definitions", workspace: str = ".") -> str:
        """Fast in-memory symbol lookup. query_type can be 'definitions', 'callers', or 'callees'."""
        idx = SymdexIndex(root=workspace)
        idx.build_index()
        if query_type == "callers":
            res = idx.find_callers(symbol)
        elif query_type == "callees":
            res = idx.find_callees(symbol)
        else:
            res = idx.find_definition(symbol)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('symdex_query'))
    def symdex_query(symbol: str, query_type: str = "definitions", workspace: str = ".") -> str:
        """Legacy alias: Fast in-memory symbol lookup."""
        return symnexus_query(symbol, query_type=query_type, workspace=workspace)

    @server.tool(annotations=tool_annotations('titandelta_memory_update'))
    def titandelta_memory_update(fact: str, workspace: str = ".") -> str:
        """Stores a fact in the TitanDelta test-time neural memory module (arXiv:2501.00663)."""
        mem = TitansMemory(root=workspace)
        mem.load()
        loss = mem.write(fact)
        mem.save()
        return json.dumps({"status": "recorded", "fact": fact, "surprise_loss": round(loss, 6)}, indent=2)

    @server.tool(annotations=tool_annotations('titans_memory_update'))
    def titans_memory_update(fact: str, workspace: str = ".") -> str:
        """Legacy alias: Stores a fact in test-time neural memory."""
        return titandelta_memory_update(fact, workspace=workspace)

    @server.tool(annotations=tool_annotations('titandelta_memory_recall'))
    def titandelta_memory_recall(query: str, top_k: int = 5, workspace: str = ".") -> str:
        """Recalls relevant memories using associative test-time memory weights."""
        mem = TitansMemory(root=workspace)
        mem.load()
        results = mem.read(query, top_k=top_k)
        return json.dumps({"query": query, "recalled": results}, indent=2)

    @server.tool(annotations=tool_annotations('titans_memory_recall'))
    def titans_memory_recall(query: str, top_k: int = 5, workspace: str = ".") -> str:
        """Legacy alias: Recalls memories using associative test-time memory weights."""
        return titandelta_memory_recall(query, top_k=top_k, workspace=workspace)

    @server.tool(annotations=tool_annotations('toolmender_repair_output'))
    def toolmender_repair_output(raw_output: str) -> str:
        """Repairs malformed JSON, fixes single-quote strings, and extracts balanced JSON from LLM text."""
        extracted = extract_outer_json(raw_output)
        if not extracted:
            return json.dumps({"error": "No JSON block found in output", "raw": raw_output})
        repaired = repair_json_string(extracted)
        try:
            parsed = json.loads(repaired)
            return json.dumps({"valid": True, "data": parsed}, indent=2)
        except Exception as e:
            return json.dumps({"valid": False, "repaired_string": repaired, "error": str(e)}, indent=2)

    @server.tool(annotations=tool_annotations('toolcall_repair_output'))
    def toolcall_repair_output(raw_output: str) -> str:
        """Legacy alias: Repairs malformed JSON and extracts balanced JSON."""
        return toolmender_repair_output(raw_output)

    @server.tool(annotations=tool_annotations('sieve_compact_logs'))
    def sieve_compact_logs(log_text: str, context_window: int = 2, max_lines: int = 60) -> str:
        """Compacts terminal logs down to root causes, failures, and stack traces, pruning 95%+ noise."""
        result = compact_text(log_text, context_window=context_window, max_lines=max_lines)
        return json.dumps(result, indent=2)

    @server.tool(annotations=tool_annotations('task_horizon_record'))
    def task_horizon_record(tool_name: str, arguments: str, outcome: str, workspace: str = ".") -> str:
        """Records an action in the task DAG and checks against the anti-loop circuit breaker."""
        mgr = HorizonManager(root=workspace)
        status = mgr.record_action(tool_name, arguments, outcome)
        return json.dumps(status, indent=2)

    @server.tool(annotations=tool_annotations('horizon_record_step'))
    def horizon_record_step(tool_name: str, arguments: str, outcome: str, workspace: str = ".") -> str:
        """Legacy alias: Records an action in the task DAG."""
        return task_horizon_record(tool_name, arguments, outcome, workspace=workspace)

    @server.tool(annotations=tool_annotations('phasegate_triage_tools'))
    def phasegate_triage_tools(prompt: str, tools_json: str, threshold: float = 0.15) -> str:
        """System-1 vector router that prunes unneeded tools using 256-dim phase vectors before model calls."""
        try:
            tools = json.loads(tools_json)
        except Exception:
            return json.dumps({"error": "tools_json must be a valid JSON array"})
        res = route_tools(prompt, tools, threshold=threshold)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('fastgate_triage_tools'))
    def fastgate_triage_tools(prompt: str, tools_json: str, threshold: float = 0.15) -> str:
        """Legacy alias: System-1 vector router."""
        return phasegate_triage_tools(prompt, tools_json, threshold=threshold)

    @server.tool(annotations=tool_annotations('snap_scratchpad'))
    def snap_scratchpad(action: str = "status", fact: str = "", hypothesis: str = "", workspace: str = ".") -> str:
        """Maintains a rolling VRAM-capped structured scratchpad under 800 tokens. Actions: 'status', 'add_fact', 'set_hypothesis'."""
        mgr = CompactKVManager(root=workspace)
        if action == "add_fact" and fact:
            res = mgr.add_fact(fact)
        elif action == "set_hypothesis" and hypothesis:
            res = mgr.set_hypothesis(hypothesis)
        else:
            res = mgr.get_state()
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('compact_kv_scratchpad'))
    def compact_kv_scratchpad(action: str = "status", fact: str = "", hypothesis: str = "", workspace: str = ".") -> str:
        """Legacy alias: Rolling structured scratchpad."""
        return snap_scratchpad(action=action, fact=fact, hypothesis=hypothesis, workspace=workspace)

    @server.tool(annotations=tool_annotations('delta_rewind_snapshot'))
    def delta_rewind_snapshot(message: str = "checkpoint", workspace: str = ".") -> str:
        """Captures a content-addressed snapshot of the workspace for microsecond rollback."""
        engine = RewindEngine(root=workspace)
        res = engine.snapshot(message=message)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('rewind_snapshot_workspace'))
    def rewind_snapshot_workspace(message: str = "checkpoint", workspace: str = ".") -> str:
        """Legacy alias: Captures workspace snapshot."""
        return delta_rewind_snapshot(message=message, workspace=workspace)

    @server.tool(annotations=tool_annotations('delta_rewind_rollback'))
    def delta_rewind_rollback(checkpoint_index: int = -1, workspace: str = ".") -> str:
        """Rolls back the workspace to the specified checkpoint index (-1 for latest)."""
        engine = RewindEngine(root=workspace)
        res = engine.rollback(checkpoint_index=checkpoint_index)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('rewind_rollback_workspace'))
    def rewind_rollback_workspace(checkpoint_index: int = -1, workspace: str = ".") -> str:
        """Legacy alias: Rolls back the workspace."""
        return delta_rewind_rollback(checkpoint_index=checkpoint_index, workspace=workspace)

    @server.tool(annotations=tool_annotations('pathsentry_audit'))
    def pathsentry_audit(directory: str = ".") -> str:
        """Audits directory paths for Windows reserved device names, illegal chars, and traversal risks."""
        res = audit_directory(directory)
        return json.dumps(res.to_dict(), indent=2)

    @server.tool(annotations=tool_annotations('path_carry_audit'))
    def path_carry_audit(directory: str = ".") -> str:
        """Legacy alias: Audits directory paths."""
        return pathsentry_audit(directory=directory)

    @server.tool(annotations=tool_annotations('drift_evaluate_action'))
    def drift_evaluate_action(goal: str, action: str) -> str:
        """Calculates trajectory angular drift in degrees [0-180] (warn >=65°, block >=80°)."""
        from app.engines import evaluate_drift
        return json.dumps(evaluate_drift(goal, action), indent=2)

    @server.tool(annotations=tool_annotations('state_epoch_check'))
    def state_epoch_check(entity_id: str, updates_json: str, expected_version: int = 1) -> str:
        """Verifies optimistic concurrency state update against StateEpoch version leases."""
        from app.engines import StateFreshStore
        store = StateFreshStore()
        try:
            updates = json.loads(updates_json)
        except Exception:
            return json.dumps({"error": "updates_json must be valid JSON"})
        decision = store.apply_update(entity_id, expected_version, updates)
        return json.dumps(decision.to_dict(), indent=2)

    @server.tool(annotations=tool_annotations('statefresh_check_update'))
    def statefresh_check_update(entity_id: str, updates_json: str, expected_version: int = 1) -> str:
        """Legacy alias: Verifies optimistic concurrency state update."""
        return state_epoch_check(entity_id, updates_json, expected_version=expected_version)

    @server.tool(annotations=tool_annotations('proofgraph_verify_step'))
    def proofgraph_verify_step(step_id: str, command: str, inputs_csv: str = "", request_id: str = "") -> str:
        """Executes or retrieves cached cryptographic proof for a verified workflow step.

        MCP requests first propose an exact command for operator review. A stored
        proof never authorizes execution; only an approved sandbox receipt does.
        """
        from app.meta.environment import ExecutionEnvironment
        from app.meta.manifest import EnvironmentConfig
        environment = ExecutionEnvironment(EnvironmentConfig(id="mcp", name="MCP workspace"), scope="mcp")
        inputs = [i.strip() for i in inputs_csv.split(",") if i.strip()]
        result = environment.execute_command(command, request_id=request_id or None, input_paths=inputs)
        return json.dumps({"step_id": step_id, **result}, indent=2)

    @server.tool(annotations=tool_annotations('workflowproof_verify_step'))
    def workflowproof_verify_step(step_id: str, command: str, inputs_csv: str = "", request_id: str = "") -> str:
        """Legacy alias: Cryptographic workflow proof verification."""
        return proofgraph_verify_step(step_id, command, inputs_csv=inputs_csv, request_id=request_id)

    @server.tool(annotations=tool_annotations('cognitive_shield_forecast'))
    def cognitive_shield_forecast(action: str, goal: str = "") -> str:
        """Pre-simulates candidate actions against hazard rules and cyclic loops."""
        from app.engines import CortexEngine
        cortex = CortexEngine()
        return json.dumps(cortex.check_action(action, goal=goal if goal else None), indent=2)

    @server.tool(annotations=tool_annotations('cortex_shield_forecast'))
    def cortex_shield_forecast(action: str, goal: str = "") -> str:
        """Legacy alias: Pre-simulates candidate actions against hazard rules."""
        return cognitive_shield_forecast(action, goal=goal)

    @server.tool(annotations=tool_annotations('pareto_triad_evaluate'))
    def pareto_triad_evaluate(workflow_id: str, reliability: float, duration_s: float, cost_tokens: int) -> str:
        """Records and evaluates Pareto efficiency across (reliability, duration, cost)."""
        from app.engines import TriadEngine
        triad = TriadEngine()
        metric = triad.record_run(workflow_id, reliability, duration_s, cost_tokens)
        rankings = triad.rank_pareto_front()
        return json.dumps({"recorded": metric.to_dict(), "pareto_rankings": rankings}, indent=2)

    @server.tool(annotations=tool_annotations('triad_evaluate_workflow'))
    def triad_evaluate_workflow(workflow_id: str, reliability: float, duration_s: float, cost_tokens: int) -> str:
        """Legacy alias: Records and evaluates Pareto efficiency."""
        return pareto_triad_evaluate(workflow_id, reliability, duration_s, cost_tokens)

    @server.tool(annotations=tool_annotations('mojo_memory_store_lesson'))
    def mojo_memory_store_lesson(text: str, evidence_json: str = "{}") -> str:
        """Stores a lesson and evidence in Mojo phase-vector associative memory."""
        from app.engines import MojoMemoryEngine
        mem = MojoMemoryEngine()
        try:
            ev = json.loads(evidence_json)
        except Exception:
            ev = {}
        return json.dumps(mem.put_lesson(text, evidence=ev), indent=2)

    @server.tool(annotations=tool_annotations('mojo_memory_search_lesson'))
    def mojo_memory_search_lesson(query: str, limit: int = 3) -> str:
        """Recalls relevant lessons and evidence using 512-dim phase vector cosine similarity."""
        from app.engines import MojoMemoryEngine
        mem = MojoMemoryEngine()
        return json.dumps(mem.search_lessons(query, limit=limit), indent=2)

    @server.tool(annotations=tool_annotations('studio_compile_prompt'))
    def studio_compile_prompt(
        subject: str,
        camera: str = "full_frame_cine",
        lens: str = "classic_anamorphic",
        focal_length_mm: int = 35,
        aperture: str = "f/1.8",
        lighting: str = "golden_hour",
        motion: str = "slow tracking shot",
    ) -> str:
        """Compiles an authoritative cinematic visual prompt with camera, lens, lighting, and motion rigs."""
        from app.engines.studio import StudioPromptCompiler
        compiled = StudioPromptCompiler.compile_cinematic_prompt(
            subject=subject,
            camera=camera,
            lens=lens,
            focal_length_mm=focal_length_mm,
            aperture=aperture,
            lighting=lighting,
            motion=motion,
        )
        return json.dumps(compiled, indent=2)

    @server.tool(annotations=tool_annotations('studio_create_storyboard'))
    def studio_create_storyboard(title: str, shots_json: str) -> str:
        """Generates a multi-shot cinematic storyboard sequence with camera movement and duration pacing."""
        from app.engines.studio import StudioAgentEngine
        studio = StudioAgentEngine()
        try:
            shots_list = json.loads(shots_json)
        except Exception:
            shots_list = [{"description": shots_json, "duration": 4.0}]
        board = studio.create_storyboard(title=title, shots_spec=shots_list)
        return json.dumps(board, indent=2)

    @server.tool(annotations=tool_annotations('studio_export_diffusion_graph'))
    def studio_export_diffusion_graph(
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        steps: int = 25,
    ) -> str:
        """Exports a production-ready diffusion execution graph for Flux Dev / SDXL."""
        from app.engines.studio import StudioAgentEngine
        studio = StudioAgentEngine()
        graph = studio.export_diffusion_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            steps=steps,
        )
        return json.dumps(graph, indent=2)

    @server.tool(annotations=tool_annotations('studio_export_comfyui_graph'))
    def studio_export_comfyui_graph(
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        steps: int = 25,
    ) -> str:
        """Legacy alias: Exports a production-ready diffusion execution graph for Flux Dev / SDXL."""
        return studio_export_diffusion_graph(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            steps=steps,
        )

    @server.tool(annotations=tool_annotations('studio_craft_banner'))
    def studio_craft_banner(platform: str, headline: str, subtext: str, style: str = "bold_typography_glassmorphism") -> str:
        """Crafts pixel-perfect banner specs with safe-zone buffers for social and web."""
        from app.engines.studio import StudioAgentEngine
        studio = StudioAgentEngine()
        spec = studio.craft_banner_spec(platform=platform, headline=headline, subtext=subtext, style=style)
        return json.dumps(spec, indent=2)

    @server.tool(annotations=tool_annotations('design_build_landing_page'))
    def design_build_landing_page(
        project_name: str,
        headline: str,
        subheadline: str,
        features_json: str = "[]",
        metrics_json: str = "[]",
        theme_primary: str = "#6366F1",
    ) -> str:
        """Generates a complete, responsive dark-mode landing page with Impeccable craft tokens."""
        from app.engines.design import DesignAgentEngine
        engine = DesignAgentEngine()
        try:
            feats = json.loads(features_json)
        except Exception:
            feats = None
        try:
            mets = json.loads(metrics_json)
        except Exception:
            mets = None
        res = engine.build_landing_page(
            project_name=project_name,
            headline=headline,
            subheadline=subheadline,
            features=feats,
            metrics=mets,
            theme_primary=theme_primary,
        )
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('design_build_dashboard'))
    def design_build_dashboard(
        dashboard_title: str,
        stats_json: str = "[]",
        activity_json: str = "[]",
    ) -> str:
        """Generates an enterprise Buzburg GUI dashboard layout."""
        from app.engines.design import DesignAgentEngine
        engine = DesignAgentEngine()
        try:
            stats = json.loads(stats_json)
        except Exception:
            stats = [{"label": "Active Agents", "value": "12", "delta": "+20%"}]
        try:
            activity = json.loads(activity_json)
        except Exception:
            activity = [{"agent": "Atlas", "action": "Task DAG dispatched", "status": "ok", "time": "Just now"}]
        res = engine.build_admin_dashboard(dashboard_title=dashboard_title, stats=stats, recent_activity=activity)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('writer_audit_prose'))
    def writer_audit_prose(text: str) -> str:
        """Audits prose for 200+ banned AI phrases, inflation words, and cadence uniformity."""
        from app.engines.writer import WriterAgentEngine
        writer = WriterAgentEngine()
        return json.dumps(writer.audit_prose(text), indent=2)

    @server.tool(annotations=tool_annotations('writer_clean_prose'))
    def writer_clean_prose(text: str) -> str:
        """Programmatically strips zero-tolerance AI clichés and restores authentic human texture."""
        from app.engines.writer import WriterAgentEngine
        writer = WriterAgentEngine()
        return json.dumps(writer.clean_prose(text), indent=2)

    @server.tool(annotations=tool_annotations('writer_plan_book'))
    def writer_plan_book(title: str, genre: str, chapters_json: str) -> str:
        """Plans a multi-chapter book or novel with word budgets, POV, and conflicts."""
        from app.engines.writer import WriterAgentEngine
        writer = WriterAgentEngine()
        try:
            chaps = json.loads(chapters_json)
        except Exception:
            chaps = [{"title": "Chapter 1", "summary": chapters_json, "words": 2500}]
        return json.dumps(writer.plan_book(title=title, genre=genre, chapters_data=chaps), indent=2)

    @server.tool(annotations=tool_annotations('design_build_swarmojo_hud'))
    def design_build_swarmojo_hud(
        system_title: str = "Swarmojo HUD",
        roster_json: str = "[]",
        milestones_json: str = "[]",
    ) -> str:
        """Generates an ultra-sleek, Buzburg-themed glassmorphism Swarmojo HUD with honey-gold and dark charcoal palette."""
        from app.engines.design import DesignAgentEngine
        engine = DesignAgentEngine()
        try:
            roster = json.loads(roster_json) if roster_json and roster_json != "[]" else None
        except Exception:
            roster = None
        try:
            milestones = json.loads(milestones_json) if milestones_json and milestones_json != "[]" else None
        except Exception:
            milestones = None
        res = engine.build_swarmojo_hud(
            system_title=system_title,
            agents_roster=roster,
            live_dag_milestones=milestones,
        )
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('design_build_herald_hud'))
    def design_build_herald_hud(
        system_title: str = "Swarmojo HUD",
        roster_json: str = "[]",
        milestones_json: str = "[]",
    ) -> str:
        """Legacy alias: Generates an ultra-sleek glassmorphism operating desktop HUD by Buzburg AI."""
        return design_build_swarmojo_hud(
            system_title=system_title,
            roster_json=roster_json,
            milestones_json=milestones_json,
        )

    @server.tool(annotations=tool_annotations('workflow_run_dag'))
    def workflow_run_dag(workflow_id: str, name: str, steps_json: str) -> str:
        """Executes a workflow DAG with constitutional governance and WorkflowProof verification."""
        from app.engines.workflow_automation import WorkflowAutomationEngine
        engine = WorkflowAutomationEngine()
        try:
            steps_data = json.loads(steps_json)
        except Exception:
            steps_data = [{"id": "step_1", "name": name, "action": "query", "params": {}}]
        dag = engine.create_workflow(workflow_id=workflow_id, name=name, steps_data=steps_data)
        res = engine.run_workflow(dag)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('workflow_schedule_routine'))
    def workflow_schedule_routine(routine_id: str, name: str, schedule: str, workflow_id: str) -> str:
        """Schedules a recurring background automation routine with cron/interval timing."""
        from app.engines.workflow_automation import WorkflowAutomationEngine
        engine = WorkflowAutomationEngine()
        res = engine.schedule_routine(routine_id=routine_id, name=name, schedule=schedule, workflow_id=workflow_id)
        return json.dumps(res, indent=2)

    @server.tool(annotations=tool_annotations('workflow_list_routines'))
    def workflow_list_routines() -> str:
        """Lists all active and scheduled background automation routines."""
        from app.engines.workflow_automation import WorkflowAutomationEngine
        engine = WorkflowAutomationEngine()
        return json.dumps(engine.list_routines(), indent=2)

    @server.tool(annotations=tool_annotations('assistant_get_briefing'))
    def assistant_get_briefing() -> str:
        """Assembles the user's daily morning briefing, agenda, and system health status."""
        from app.engines.personal_assistant import PersonalAssistantEngine
        assistant = PersonalAssistantEngine()
        return json.dumps(assistant.get_briefing(), indent=2)

    @server.tool(annotations=tool_annotations('assistant_consult_specialist'))
    def assistant_consult_specialist(goal: str, division: str = "general") -> str:
        """Delegates a high-level goal to specialist agent guilds and synthesizes results."""
        from app.engines.personal_assistant import PersonalAssistantEngine
        assistant = PersonalAssistantEngine()
        return json.dumps(assistant.consult_specialist(goal=goal, division=division), indent=2)

    @server.tool(annotations=tool_annotations('assistant_store_credential'))
    def assistant_store_credential(key_name: str, secret_val: str) -> str:
        """Stores a sensitive credential in the local encrypted assistant vault."""
        from app.engines.personal_assistant import PersonalAssistantEngine
        assistant = PersonalAssistantEngine()
        return json.dumps(assistant.store_credential(key_name=key_name, secret_val=secret_val), indent=2)

    # -------------------------------------------------------------------------
    # Harness Governance, Org Chart, Budgets, Heartbeats & Approvals
    # -------------------------------------------------------------------------

    @server.tool(annotations=tool_annotations('harness_get_org_chart'))
    def harness_get_org_chart() -> str:
        """Retrieves company organizational hierarchy, reporting lines, and headcount."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        return json.dumps(engine.get_org_chart(), indent=2)

    @server.tool(annotations=tool_annotations('harness_hire_agent'))
    def harness_hire_agent(
        agent_id: str,
        name: str,
        role: str,
        tier: str = "specialist",
        reports_to: str = "",
        model: str = "default",
        budget_cap_usd: float = 30.0,
        avatar: str = "🤖",
    ) -> str:
        """Hires a new agent into the organizational hierarchy with budget and reporting lines."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        return json.dumps(
            engine.hire_agent(
                agent_id=agent_id,
                name=name,
                role=role,
                tier=tier,
                reports_to=reports_to or None,
                model=model,
                budget_cap_usd=budget_cap_usd,
                avatar=avatar,
            ),
            indent=2,
        )

    @server.tool(annotations=tool_annotations('harness_get_budgets'))
    def harness_get_budgets() -> str:
        """Returns budget spending summaries, hard caps, and token usage per agent."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        return json.dumps(engine.get_budget_summary(), indent=2)

    @server.tool(annotations=tool_annotations('harness_trigger_heartbeat'))
    def harness_trigger_heartbeat(agent_id: str = "") -> str:
        """Dispatches an on-demand heartbeat pulse to wake agents and trigger pending work."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        aid = agent_id.strip() if agent_id.strip() else None
        return json.dumps(engine.trigger_heartbeat(agent_id=aid), indent=2)

    @server.tool(annotations=tool_annotations('harness_list_tasks'))
    def harness_list_tasks() -> str:
        """Returns task issues organized by Kanban columns (backlog, in_progress, blocked, review, done)."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        return json.dumps(engine.list_tasks(), indent=2)

    @server.tool(annotations=tool_annotations('harness_create_task'))
    def harness_create_task(
        task_id: str,
        title: str,
        description: str,
        assignee_id: str = "atlas",
        priority: str = "medium",
        blocked_by_json: str = "[]",
    ) -> str:
        """Creates a new goal or task issue with priority and blocking dependencies."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        try:
            blocked_by = json.loads(blocked_by_json)
        except Exception:
            blocked_by = []
        return json.dumps(
            engine.create_task(
                task_id=task_id,
                title=title,
                description=description,
                assignee_id=assignee_id,
                priority=priority,
                blocked_by=blocked_by,
            ),
            indent=2,
        )

    @server.tool(annotations=tool_annotations('harness_list_approvals'))
    def harness_list_approvals(pending_only: bool = True) -> str:
        """Lists gated actions requiring human authorization (git pushes, deploys, large spends)."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        return json.dumps(engine.list_approvals(pending_only=pending_only), indent=2)

    @server.tool(annotations=tool_annotations('harness_resolve_approval'))
    def harness_resolve_approval(approval_id: str, action: str = "approve", approver: str = "HumanAdmin") -> str:
        """Approves or rejects a gated action."""
        from app.engines.governance import HarnessGovernanceEngine
        return json.dumps({"ok": False, "error": "Operator-only action: use the local governance CLI"})

    @server.tool(annotations=tool_annotations('harness_get_settings'))
    def harness_get_settings() -> str:
        """Returns runtime harness options including BYOA connectors and concurrency modes."""
        from app.engines.governance import HarnessGovernanceEngine
        engine = HarnessGovernanceEngine()
        return json.dumps(engine.get_settings(), indent=2)







