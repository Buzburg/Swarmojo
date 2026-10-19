"""Conservative MCP capability hints and explicit local-plugin selection."""
import os
from pathlib import Path
import re

# Read operations may initialize local indexes/caches. They do not edit user content.
READ_TOOLS = frozenset('''
list_knowledge_documents get_file_watcher_status get_ticket list_tickets
get_system_metrics list_skills get_tool_health_report get_zg_facets list_topics
roms_sieve_compact roms_titans_recall roms_symdex_lookup roms_shield_forecast
roms_shield_repair_json roms_prompt_lookup symnexus_query symdex_query
 titandelta_memory_recall titans_memory_recall toolmender_repair_output
 toolcall_repair_output sieve_compact_logs phasegate_triage_tools fastgate_triage_tools
 pathsentry_audit path_carry_audit drift_evaluate_action cognitive_shield_forecast
 cortex_shield_forecast mojo_memory_search_lesson writer_audit_prose writer_clean_prose
 workflow_list_routines harness_get_org_chart harness_get_budgets harness_list_tasks
 harness_list_approvals harness_get_settings meta_list_agents meta_list_teams
 meta_list_models coding_read_slice coding_find_files coding_grep coding_symdex_callgraph
 coding_drift_evaluate coding_review_code coding_inspect_binary coding_repo_codemap
 meta_immunity_check meta_antibody_check memory_get memory_recall memory_prepare_context
 calculate_refund_amount search_codebase find_symbol_definition
'''.split())
# These may call a configured embedding/model/search provider, even during retrieval.
NETWORK_TOOLS = frozenset('''
search_knowledge_base search_grounded_context search_by_topic search_tools zg_search
swarmmojo_prepare_harness roms_prepare_harness add_knowledge_document reload_knowledge
 autokarpathy_generate_dataset autokarpathy_optimize_prompt autokarpathy_eval_cartridge
 autoresearch meta_run_team coding_subagent_delegate
'''.split())
DESTRUCTIVE_TOOLS = frozenset('''
memory_forget roms_titans_erase delta_rewind_rollback rewind_rollback_workspace roms_snapshot_rewind
'''.split())
EXECUTION_TOOLS = frozenset('''
meta_execute_approved meta_dedup_run meta_once_run run_sandboxed_command
proofgraph_verify_step workflowproof_verify_step workflow_run_dag
'''.split())


def tool_annotations(name):
    """Conservative hints for registered tools, including legacy aliases."""
    read = name in READ_TOOLS
    return dict(readOnlyHint=read, destructiveHint=not read,
                idempotentHint=read, openWorldHint=name in NETWORK_TOOLS or name in EXECUTION_TOOLS)


def plugin_allowed(path: Path, root: Path, *, reload=False):
    """Only explicitly named local Python plugins may be imported; links are rejected."""
    if os.getenv('SWARMOJO_MCP_PROFILE', 'read_only') != 'local':
        return False
    if reload and os.getenv('SWARMOJO_MCP_HOT_RELOAD') != '1':
        return False
    names = {name.strip() for name in os.getenv('SWARMOJO_MCP_PLUGINS', '').split(',') if name.strip()}
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) for name in names):
        raise ValueError('SWARMOJO_MCP_PLUGINS must contain comma-separated Python module names')
    return (path.stem in names and path.suffix == '.py' and not root.is_symlink()
            and not path.is_symlink() and path.is_file() and path.resolve().parent == root.resolve())
