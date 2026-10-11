"""Design Agent Engine for Swarmojo by Buzburg AI.

High-craft UI, GUI, and Website generation engine:
- Buzburg Impeccable Craft Floor: WCAG AAA contrast, typographic measures, subtle depth, zero-halo shadows
- Buzburg Design System: enterprise tokens, components, banner layouts, responsive safe-zones
- Buzburg Multi-Stage Web Pipeline: PM -> Designer -> Developer -> Reviewer for single & multi-page websites
- Buzburg Enterprise Admin Panels: data tables, metric delta widgets, modern forms
- Buzburg UI Component Registry: cards, dialogs, navbars, charts, hero sections
- Buzburg Desktop & Web GUI canvas layout generation
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# -------------------------------------------------------------------------
# Impeccable Design Token System & Craft Floor
# -------------------------------------------------------------------------

@dataclass
class DesignTokens:
    font_sans: str = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    font_mono: str = "'JetBrains Mono', 'Fira Code', monospace"
    font_display: str = "'Plus Jakarta Sans', Inter, sans-serif"
    primary: str = "#6366F1"        # Indigo
    primary_hover: str = "#4F46E5"
    background: str = "#0B0F19"     # Deep slate void
    surface: str = "#111827"        # Card / panel surface
    surface_border: str = "#1F2937" # 1px subtle divider
    text_primary: str = "#F9FAFB"   # High contrast >=7:1
    text_secondary: str = "#9CA3AF" # Medium contrast >=4.5:1
    accent: str = "#06B6D4"         # Cyan highlight
    danger: str = "#EF4444"
    success: str = "#10B981"
    border_radius: str = "12px"
    shadow_card: str = "0 4px 20px -2px rgba(0, 0, 0, 0.4), 0 2px 6px -1px rgba(0, 0, 0, 0.2)"
    shadow_elevated: str = "0 10px 30px -4px rgba(0, 0, 0, 0.5), 0 4px 12px -2px rgba(0, 0, 0, 0.3)"

    def to_css(self) -> str:
        return f"""
:root {{
  --font-sans: {self.font_sans};
  --font-mono: {self.font_mono};
  --font-display: {self.font_display};
  --color-primary: {self.primary};
  --color-primary-hover: {self.primary_hover};
  --color-bg: {self.background};
  --color-surface: {self.surface};
  --color-surface-border: {self.surface_border};
  --color-text-primary: {self.text_primary};
  --color-text-secondary: {self.text_secondary};
  --color-accent: {self.accent};
  --color-danger: {self.danger};
  --color-success: {self.success};
  --radius-card: {self.border_radius};
  --shadow-card: {self.shadow_card};
  --shadow-elevated: {self.shadow_elevated};
}}
"""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# -------------------------------------------------------------------------
# Component Registry & Layout Generator
# -------------------------------------------------------------------------

class UIComponentRegistry:
    """Standardized production UI component generator (HTML5 + Tailwind / Modern CSS)."""

    @classmethod
    def render_navbar(cls, brand_name: str, links: List[Dict[str, str]], cta_label: str = "Get Started") -> str:
        links_html = "\n".join([f'<a href="{l.get("href", "#")}" class="nav-link">{l.get("label", "")}</a>' for l in links])
        return f"""
<header class="site-header">
  <div class="header-container">
    <div class="brand">
      <span class="brand-logo">◆</span>
      <span class="brand-name">{brand_name}</span>
    </div>
    <nav class="nav-menu">
      {links_html}
    </nav>
    <div class="header-actions">
      <button class="btn btn-primary">{cta_label}</button>
    </div>
  </div>
</header>
"""

    @classmethod
    def render_hero(cls, badge: str, title: str, subtitle: str, primary_cta: str, secondary_cta: str) -> str:
        return f"""
<section class="hero-section">
  <div class="hero-glow"></div>
  <div class="hero-container">
    <div class="badge-pill">
      <span class="badge-dot"></span>
      <span class="badge-text">{badge}</span>
    </div>
    <h1 class="hero-title">{title}</h1>
    <p class="hero-subtitle">{subtitle}</p>
    <div class="hero-cta-group">
      <button class="btn btn-primary btn-lg">{primary_cta}</button>
      <button class="btn btn-secondary btn-lg">{secondary_cta}</button>
    </div>
  </div>
</section>
"""

    @classmethod
    def render_feature_grid(cls, features: List[Dict[str, str]]) -> str:
        cards = []
        for f in features:
            cards.append(f"""
    <div class="feature-card">
      <div class="feature-icon">{f.get('icon', '⚡')}</div>
      <h3 class="feature-title">{f.get('title', 'Feature')}</h3>
      <p class="feature-desc">{f.get('description', '')}</p>
    </div>
""")
        return f"""
<section class="features-section">
  <div class="features-container">
    <div class="features-grid">
      {''.join(cards)}
    </div>
  </div>
</section>
"""

    @classmethod
    def render_metrics_panel(cls, metrics: List[Dict[str, str]]) -> str:
        items = []
        for m in metrics:
            items.append(f"""
    <div class="metric-item">
      <span class="metric-value">{m.get('value', '0')}</span>
      <span class="metric-label">{m.get('label', 'Metric')}</span>
    </div>
""")
        return f"""
<section class="metrics-section">
  <div class="metrics-container">
    {''.join(items)}
  </div>
</section>
"""


# -------------------------------------------------------------------------
# Complete Website & Admin Dashboard Page Builder
# -------------------------------------------------------------------------

class DesignAgentEngine:
    """Master UI, GUI, and Website design engine."""

    def __init__(self, workspace_root: str = "."):
        self.root = Path(workspace_root).resolve()
        self.output_dir = self.root / ".mojo_design"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tokens = DesignTokens()

    def build_landing_page(
        self,
        project_name: str,
        headline: str,
        subheadline: str,
        features: Optional[List[Dict[str, str]]] = None,
        metrics: Optional[List[Dict[str, str]]] = None,
        theme_primary: str = "#6366F1",
    ) -> Dict[str, Any]:
        """Generates a complete, responsive, dark-mode landing page with Impeccable craft."""
        self.tokens.primary = theme_primary
        self.tokens.primary_hover = theme_primary

        feature_list = features or [
            {"icon": "⚡", "title": "Microsecond Execution", "description": "Native Mojo-accelerated kernels delivering sub-10 µs symbol indices and tool triage."},
            {"icon": "🛡️", "title": "StateFresh OCC", "description": "Optimistic concurrency control with cryptographic fingerprinting to prevent stale overwrites."},
            {"icon": "🧠", "title": "Associative Memory", "description": "512-dimensional phase-vector memory with surprise-gated Titans test-time learning."},
            {"icon": "🎬", "title": "Directorial Studio", "description": "Multimodal video pipelines with 70mm camera rigs and diffusion graph synthesis."},
        ]

        metric_list = metrics or [
            {"value": "15x", "label": "Faster Tool Triage"},
            {"value": "99.9%", "label": "Concurrency Safety"},
            {"value": "<20µs", "label": "Call Graph Lookup"},
            {"value": "0-Token", "label": "Offline Rehearsals"},
        ]

        nav = UIComponentRegistry.render_navbar(
            brand_name=project_name,
            links=[
                {"label": "Features", "href": "#features"},
                {"label": "Architecture", "href": "#architecture"},
                {"label": "Docs", "href": "#docs"},
            ],
            cta_label="Explore Harness",
        )

        hero = UIComponentRegistry.render_hero(
            badge="Swarmojo Autonomous Engine",
            title=headline,
            subtitle=subheadline,
            primary_cta="Get Started Free",
            secondary_cta="View Architecture",
        )

        metrics_html = UIComponentRegistry.render_metrics_panel(metric_list)
        features_html = UIComponentRegistry.render_feature_grid(feature_list)

        css_styles = f"""
{self.tokens.to_css()}

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  font-family: var(--font-sans);
  background-color: var(--color-bg);
  color: var(--color-text-primary);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

.site-header {{
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(12px);
  background-color: rgba(11, 15, 25, 0.8);
  border-bottom: 1px solid var(--color-surface-border);
}}

.header-container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.25rem;
}}

.brand-logo {{
  color: var(--color-primary);
}}

.nav-menu {{
  display: flex;
  gap: 2rem;
}}

.nav-link {{
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.95rem;
  font-weight: 500;
  transition: color 0.2s;
}}

.nav-link:hover {{
  color: var(--color-text-primary);
}}

.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.6rem 1.25rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}}

.btn-primary {{
  background-color: var(--color-primary);
  color: #FFFFFF;
}}

.btn-primary:hover {{
  background-color: var(--color-primary-hover);
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.4);
}}

.btn-secondary {{
  background-color: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-surface-border);
}}

.btn-secondary:hover {{
  border-color: var(--color-text-secondary);
}}

.btn-lg {{
  padding: 0.85rem 1.75rem;
  font-size: 1.05rem;
}}

.hero-section {{
  position: relative;
  padding: 6rem 1.5rem 4rem;
  text-align: center;
  overflow: hidden;
}}

.hero-glow {{
  position: absolute;
  top: -20%;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 400px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(11, 15, 25, 0) 70%);
  pointer-events: none;
}}

.hero-container {{
  max-width: 860px;
  margin: 0 auto;
  position: relative;
}}

.badge-pill {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.85rem;
  border-radius: 9999px;
  background-color: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  margin-bottom: 1.5rem;
}}

.badge-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-primary);
}}

.badge-text {{
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}}

.hero-title {{
  font-family: var(--font-display);
  font-size: 3.5rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.15;
  margin-bottom: 1.5rem;
}}

.hero-subtitle {{
  font-size: 1.25rem;
  color: var(--color-text-secondary);
  max-width: 700px;
  margin: 0 auto 2.5rem;
}}

.hero-cta-group {{
  display: flex;
  justify-content: center;
  gap: 1rem;
}}

.metrics-section {{
  border-top: 1px solid var(--color-surface-border);
  border-bottom: 1px solid var(--color-surface-border);
  background-color: rgba(17, 24, 39, 0.5);
  padding: 2.5rem 1.5rem;
}}

.metrics-container {{
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  text-align: center;
}}

.metric-value {{
  display: block;
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--color-text-primary);
}}

.metric-label {{
  font-size: 0.95rem;
  color: var(--color-text-secondary);
}}

.features-section {{
  padding: 5rem 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}}

.features-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.5rem;
}}

.feature-card {{
  background-color: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: var(--radius-card);
  padding: 2rem;
  box-shadow: var(--shadow-card);
  transition: transform 0.2s, border-color 0.2s;
}}

.feature-card:hover {{
  transform: translateY(-4px);
  border-color: var(--color-primary);
}}

.feature-icon {{
  font-size: 2rem;
  margin-bottom: 1rem;
}}

.feature-title {{
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}}

.feature-desc {{
  font-size: 0.95rem;
  color: var(--color-text-secondary);
}}
"""

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name} — {headline}</title>
  <style>
{css_styles}
  </style>
</head>
<body>
  {nav}
  {hero}
  {metrics_html}
  {features_html}
</body>
</html>
"""

        out_file = self.output_dir / "index.html"
        out_file.write_text(full_html, encoding="utf-8")

        return {
            "status": "ready",
            "file": str(out_file),
            "project_name": project_name,
            "headline": headline,
            "html_length": len(full_html),
            "tokens": self.tokens.to_dict(),
        }

    def build_admin_dashboard(
        self,
        dashboard_title: str,
        stats: List[Dict[str, str]],
        recent_activity: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generates an enterprise Buzburg GUI dashboard layout."""
        stat_cards = []
        for s in stats:
            stat_cards.append(f"""
      <div class="dash-stat-card">
        <span class="stat-title">{s.get('label', 'Stat')}</span>
        <span class="stat-number">{s.get('value', '0')}</span>
        <span class="stat-delta">{s.get('delta', '+0%')}</span>
      </div>
""")

        activity_rows = []
        for a in recent_activity:
            activity_rows.append(f"""
        <tr class="activity-row">
          <td class="col-agent">{a.get('agent', 'Agent')}</td>
          <td class="col-action">{a.get('action', 'Action')}</td>
          <td class="col-status"><span class="badge-status {a.get('status', 'ok')}">{a.get('status', 'ok')}</span></td>
          <td class="col-time">{a.get('time', 'Just now')}</td>
        </tr>
""")

        dash_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{dashboard_title} — Admin Dashboard</title>
  <style>
{self.tokens.to_css()}

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  font-family: var(--font-sans);
  background-color: var(--color-bg);
  color: var(--color-text-primary);
  display: flex;
  height: 100vh;
  overflow: hidden;
}}

.sidebar {{
  width: 260px;
  background-color: var(--color-surface);
  border-right: 1px solid var(--color-surface-border);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
}}

.sidebar-brand {{
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 2rem;
  color: var(--color-primary);
}}

.sidebar-menu {{
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}}

.sidebar-item {{
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;
}}

.sidebar-item.active, .sidebar-item:hover {{
  background-color: rgba(99, 102, 241, 0.1);
  color: var(--color-text-primary);
}}

.main-content {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}}

.top-bar {{
  padding: 1rem 2rem;
  border-bottom: 1px solid var(--color-surface-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.dash-title {{
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
}}

.content-body {{
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}}

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
}}

.dash-stat-card {{
  background-color: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: var(--radius-card);
  padding: 1.5rem;
  box-shadow: var(--shadow-card);
}}

.stat-title {{
  display: block;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
}}

.stat-number {{
  display: block;
  font-size: 2rem;
  font-weight: 700;
  font-family: var(--font-display);
  margin-bottom: 0.25rem;
}}

.stat-delta {{
  font-size: 0.85rem;
  color: var(--color-success);
}}

.table-card {{
  background-color: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: var(--radius-card);
  padding: 1.5rem;
  box-shadow: var(--shadow-card);
}}

.table-title {{
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 1rem;
}}

table {{
  width: 100%;
  border-collapse: collapse;
}}

th {{
  text-align: left;
  padding: 0.75rem 1rem;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-surface-border);
}}

td {{
  padding: 0.85rem 1rem;
  font-size: 0.95rem;
  border-bottom: 1px solid rgba(31, 41, 55, 0.5);
}}

.badge-status {{
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}}

.badge-status.success, .badge-status.ok {{
  background-color: rgba(16, 185, 129, 0.15);
  color: var(--color-success);
}}
  </style>
</head>
<body>
  <aside class="sidebar">
    <div class="sidebar-brand">◆ {dashboard_title}</div>
    <nav class="sidebar-menu">
      <a href="#" class="sidebar-item active">Overview</a>
      <a href="#" class="sidebar-item">Agents</a>
      <a href="#" class="sidebar-item">Workflows</a>
      <a href="#" class="sidebar-item">Settings</a>
    </nav>
  </aside>
  <main class="main-content">
    <header class="top-bar">
      <h1 class="dash-title">Workspace Operations</h1>
    </header>
    <div class="content-body">
      <div class="stats-grid">
        {''.join(stat_cards)}
      </div>
      <div class="table-card">
        <h2 class="table-title">Recent Activity</h2>
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Action</th>
              <th>Status</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {''.join(activity_rows)}
          </tbody>
        </table>
      </div>
    </div>
  </main>
</body>
</html>
"""

        out_file = self.output_dir / "dashboard.html"
        out_file.write_text(dash_html, encoding="utf-8")

        return {
            "status": "ready",
            "file": str(out_file),
            "dashboard_title": dashboard_title,
            "html_length": len(dash_html),
        }

    def build_swarmojo_hud(
        self,
        system_title: str = "Swarmojo HUD",
        agents_roster: Optional[List[Dict[str, Any]]] = None,
        live_dag_milestones: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generates an ultra-sleek, Buzburg-themed glassmorphism Swarmojo HUD with Org Chart, Tasks Kanban, Budgets, Approvals, and Settings."""
        roster = agents_roster or [
            {"id": "atlas", "name": "Atlas", "role": "Swarm Coordinator & Executive Lead", "tier": "executive", "status": "active", "load": "12%", "model": "deepseek-r1", "avatar": "⚡", "spent": "$14.20", "cap": "$80.00"},
            {"id": "daedalus", "name": "Daedalus", "role": "Principal DeepCode Architect", "tier": "lead", "status": "busy", "load": "78%", "model": "qwen-coder", "avatar": "🛠️", "spent": "$28.50", "cap": "$60.00"},
            {"id": "vitruvius", "name": "Vitruvius", "role": "Staff UI/UX Systems Designer", "tier": "specialist", "status": "idle", "load": "4%", "model": "qwen-coder", "avatar": "🎨", "spent": "$6.15", "cap": "$40.00"},
            {"id": "lumiere", "name": "Lumiere", "role": "Studio Director & Multimodal Producer", "tier": "specialist", "status": "rendering", "load": "94%", "model": "flux-dev", "avatar": "🎬", "spent": "$19.40", "cap": "$50.00"},
            {"id": "orwell", "name": "Orwell", "role": "Lead Ghost Scribe & Technical Writer", "tier": "specialist", "status": "active", "load": "32%", "model": "qwen-coder", "avatar": "✍️", "spent": "$4.80", "cap": "$30.00"},
            {"id": "aegis", "name": "Aegis", "role": "Chief Security Auditor & Constitutional Guard", "tier": "auditor", "status": "monitoring", "load": "8%", "model": "llama3", "avatar": "🛡️", "spent": "$5.20", "cap": "$40.00"},
        ]

        milestones = live_dag_milestones or [
            {"id": "m1", "title": "DAG Ingestion & Triage", "engine": "fastgate", "latency": "8µs", "state": "complete"},
            {"id": "m2", "title": "DeepCode Recursive Subagent Fork", "engine": "deepcode-recursion", "latency": "14ms", "state": "running"},
            {"id": "m3", "title": "Mojo Angular Drift Evaluation", "engine": "mojo-drift", "latency": "42µs", "state": "pending"},
            {"id": "m4", "title": "StateFresh OCC File Write Lease", "engine": "statefresh", "latency": "6µs", "state": "pending"},
        ]

        roster_cards = []
        for a in roster:
            status_cls = a.get("status", "idle")
            roster_cards.append(f"""
        <div class="hud-agent-card {status_cls}">
          <div class="agent-avatar">{a.get('avatar', '🤖')}</div>
          <div class="agent-info">
            <div class="agent-name-row">
              <span class="agent-name">{a.get('name')}</span>
              <span class="agent-badge {status_cls}">{status_cls}</span>
            </div>
            <span class="agent-role">{a.get('role')}</span>
            <div class="agent-meta">
              <span class="meta-tag">{a.get('model')}</span>
              <span class="meta-load">Load: {a.get('load')}</span>
            </div>
          </div>
        </div>
""")

        dag_items = []
        for m in milestones:
            st = m.get("state", "pending")
            dag_items.append(f"""
        <div class="dag-step {st}">
          <div class="step-indicator"></div>
          <div class="step-content">
            <div class="step-header">
              <span class="step-title">{m.get('title')}</span>
              <span class="step-engine">{m.get('engine')} ({m.get('latency')})</span>
            </div>
            <span class="step-state">{st.upper()}</span>
          </div>
        </div>
""")

        hud_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{system_title} — Sovereign Operations Console</title>
  <style>
:root {{
  color-scheme: dark;
  --bg-deep: #13110E;
  --bg-surface: #1A1613;
  --bg-glass: rgba(28, 24, 21, 0.82);
  --bg-card: rgba(38, 32, 27, 0.75);
  --bg-card-hover: rgba(54, 46, 38, 0.92);
  --border-glass: rgba(229, 168, 35, 0.22);
  --border-glow: rgba(229, 168, 35, 0.65);
  --accent-gold: #E5A823;
  --accent-gold-bright: #FBBF24;
  --accent-gold-dim: #B2882C;
  --accent-amber: #D97706;
  --accent-charcoal: #362D26;
  --accent-charcoal-dark: #1E1A17;
  --accent-emerald: #10B981;
  --accent-red: #EF4444;
  --text-main: #FAF8F5;
  --text-muted: #BDB4A8;
  --text-dim: #8C8276;
  --terminal-bg: #0B0908;
  --terminal-text: #FDE68A;
}}

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  background-color: var(--bg-deep);
  background-image: 
    radial-gradient(at 0% 0%, rgba(229, 168, 35, 0.16) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(54, 45, 38, 0.38) 0px, transparent 55%),
    radial-gradient(circle at 50% 25%, rgba(229, 168, 35, 0.05) 0px, transparent 60%);
  color: var(--text-main);
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}

/* Top Menu Bar */
.hud-menubar {{
  height: 48px;
  background: rgba(19, 17, 15, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-glass);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  font-size: 0.85rem;
  z-index: 100;
}}

.menubar-left {{
  display: flex;
  align-items: center;
  gap: 1.5rem;
}}

.system-brand {{
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.95rem;
}}

.menubar-right {{
  display: flex;
  align-items: center;
  gap: 1.25rem;
  color: var(--text-muted);
  font-size: 0.8rem;
}}

.btn-heartbeat {{
  background: rgba(229, 168, 35, 0.15);
  border: 1px solid var(--border-glow);
  color: var(--accent-gold-bright);
  font-weight: 700;
  font-size: 0.75rem;
  padding: 0.35rem 0.75rem;
  border-radius: 9999px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.2s ease;
}}

.btn-heartbeat:hover {{
  background: rgba(229, 168, 35, 0.3);
  box-shadow: 0 0 12px rgba(229, 168, 35, 0.4);
  transform: scale(1.03);
}}

.live-indicator {{
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: var(--accent-gold-bright);
  font-weight: 700;
  font-size: 0.8rem;
}}

.pulse-dot {{
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background-color: var(--accent-gold);
  box-shadow: 0 0 10px var(--accent-gold);
  animation: pulse 2s infinite;
}}

@keyframes pulse {{
  0% {{ opacity: 1; transform: scale(1); box-shadow: 0 0 12px var(--accent-gold); }}
  50% {{ opacity: 0.35; transform: scale(0.85); box-shadow: 0 0 4px var(--accent-gold); }}
  100% {{ opacity: 1; transform: scale(1); box-shadow: 0 0 12px var(--accent-gold); }}
}}

/* Subnav Navigation Bar (Harness Options Tabs) */
.hud-subnav {{
  height: 42px;
  background: rgba(22, 19, 16, 0.9);
  border-bottom: 1px solid var(--border-glass);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  gap: 0.5rem;
  z-index: 90;
}}

.nav-tab {{
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.55rem 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  transition: all 0.2s ease;
  height: 100%;
}}

.nav-tab:hover {{
  color: var(--text-main);
  background: rgba(229, 168, 35, 0.06);
}}

.nav-tab.active {{
  color: var(--accent-gold-bright);
  border-bottom-color: var(--accent-gold-bright);
  background: rgba(229, 168, 35, 0.1);
  font-weight: 700;
}}

.badge-counter {{
  background: #EF4444;
  color: white;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 0.1rem 0.4rem;
  border-radius: 9999px;
  margin-left: 0.2rem;
}}

/* View Containers */
.hud-view {{
  display: none;
  flex: 1;
  padding: 1.25rem;
  overflow: hidden;
}}

.hud-view.active {{
  display: flex;
  flex-direction: column;
}}

/* View 1: Telemetry Workspace (3-column layout) */
.telemetry-layout {{
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr 380px;
  gap: 1.25rem;
  overflow: hidden;
}}

/* Glassmorphism Panel */
.glass-panel {{
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.55);
}}

.panel-header {{
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--border-glass);
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.panel-title {{
  font-size: 0.92rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-main);
}}

.panel-body {{
  flex: 1;
  padding: 1.25rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}}

/* Left Column: Agent Swarm Roster */
.hud-agent-card {{
  background: var(--bg-card);
  border: 1px solid rgba(229, 168, 35, 0.12);
  border-radius: 12px;
  padding: 0.85rem;
  display: flex;
  gap: 0.85rem;
  transition: all 0.2s ease;
}}

.hud-agent-card:hover {{
  border-color: var(--border-glow);
  transform: translateY(-2px);
  background: var(--bg-card-hover);
  box-shadow: 0 4px 20px rgba(229, 168, 35, 0.16);
}}

.agent-avatar {{
  font-size: 1.35rem;
  background: rgba(229, 168, 35, 0.14);
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(229, 168, 35, 0.28);
}}

.agent-info {{ flex: 1; }}

.agent-name-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.agent-name {{
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text-main);
}}

.agent-role {{
  font-size: 0.8rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 0.35rem;
}}

.agent-meta {{
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-dim);
}}

.meta-tag {{
  background: rgba(255, 255, 255, 0.06);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  color: var(--text-muted);
  font-size: 0.7rem;
}}

.meta-load {{
  color: var(--accent-gold-dim);
  font-weight: 600;
}}

.agent-badge {{
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
}}

.agent-badge.active, .agent-badge.running {{
  background: rgba(229, 168, 35, 0.18);
  color: var(--accent-gold-bright);
  border: 1px solid rgba(229, 168, 35, 0.45);
}}

.agent-badge.busy, .agent-badge.rendering {{
  background: rgba(217, 119, 6, 0.2);
  color: #F59E0B;
  border: 1px solid rgba(217, 119, 6, 0.45);
}}

.agent-badge.idle, .agent-badge.monitoring {{
  background: rgba(140, 130, 118, 0.14);
  color: var(--text-muted);
  border: 1px solid rgba(140, 130, 118, 0.25);
}}

/* Center Console */
.center-viewport {{
  display: grid;
  grid-template-rows: 240px 1fr;
  gap: 1.25rem;
}}

.telemetry-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}}

.telemetry-card {{
  background: var(--bg-card);
  border: 1px solid rgba(229, 168, 35, 0.15);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}}

.telemetry-val {{
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}}

.telemetry-val.gold {{
  color: var(--accent-gold-bright);
  text-shadow: 0 0 16px rgba(229, 168, 35, 0.3);
}}

.telemetry-val.ivory {{ color: var(--text-main); }}
.telemetry-val.amber {{ color: #F59E0B; }}

.telemetry-lbl {{
  font-size: 0.8rem;
  color: var(--text-dim);
}}

.live-terminal {{
  background: var(--terminal-bg);
  border: 1px solid rgba(229, 168, 35, 0.2);
  border-radius: 12px;
  padding: 1rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: var(--terminal-text);
  line-height: 1.6;
  overflow-y: auto;
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.7);
}}

/* Right Panel: Live DAG Execution Milestones */
.dag-step {{
  display: flex;
  gap: 0.85rem;
  position: relative;
}}

.step-indicator {{
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 4px;
  background: var(--text-dim);
}}

.dag-step.complete .step-indicator {{
  background: var(--accent-gold);
  box-shadow: 0 0 10px var(--accent-gold);
}}

.dag-step.running .step-indicator {{
  background: var(--accent-gold-bright);
  box-shadow: 0 0 12px var(--accent-gold-bright);
  animation: pulse 1.5s infinite;
}}

.step-content {{
  flex: 1;
  background: var(--bg-card);
  padding: 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(229, 168, 35, 0.12);
}}

.step-header {{
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}}

.step-title {{
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--text-main);
}}

.step-engine {{
  font-size: 0.75rem;
  color: var(--accent-gold);
  font-weight: 600;
}}

.step-state {{
  font-size: 0.7rem;
  color: var(--text-dim);
}}

/* View 2: Org Chart Hierarchy */
.org-container {{
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
  padding: 0.5rem;
}}

.org-level {{
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  position: relative;
}}

.org-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 14px;
  padding: 1.25rem;
  width: 280px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);
  transition: all 0.2s ease;
  position: relative;
}}

.org-card:hover {{
  border-color: var(--border-glow);
  transform: translateY(-3px);
  box-shadow: 0 8px 28px rgba(229, 168, 35, 0.2);
}}

.org-tier-tag {{
  position: absolute;
  top: 10px;
  right: 12px;
  font-size: 0.65rem;
  font-weight: 800;
  text-transform: uppercase;
  color: var(--accent-gold-bright);
  background: rgba(229, 168, 35, 0.15);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}}

.org-card-header {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
}}

.org-card-avatar {{
  font-size: 1.8rem;
  width: 48px;
  height: 48px;
  background: rgba(229, 168, 35, 0.15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(229, 168, 35, 0.3);
}}

.org-card-name {{
  font-weight: 800;
  font-size: 1.05rem;
}}

.org-card-role {{
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.3;
}}

.org-card-stats {{
  display: flex;
  justify-content: space-between;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.75rem;
}}

/* View 3: Tasks & Goals Kanban Board */
.kanban-board {{
  flex: 1;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
  overflow-x: auto;
}}

.kanban-col {{
  background: rgba(24, 20, 17, 0.75);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

.kanban-col-header {{
  padding: 0.75rem 1rem;
  background: rgba(35, 29, 25, 0.8);
  border-bottom: 1px solid var(--border-glass);
  font-weight: 700;
  font-size: 0.85rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.kanban-col-body {{
  flex: 1;
  padding: 0.75rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}}

.kanban-card {{
  background: var(--bg-card);
  border: 1px solid rgba(229, 168, 35, 0.15);
  border-radius: 10px;
  padding: 0.85rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}}

.kanban-card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}}

.task-id {{
  font-size: 0.7rem;
  font-family: monospace;
  color: var(--accent-gold);
  font-weight: 700;
}}

.task-priority {{
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  text-transform: uppercase;
}}

.task-priority.critical {{ background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
.task-priority.high {{ background: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); }}
.task-priority.medium {{ background: rgba(140, 130, 118, 0.2); color: var(--text-muted); }}

.task-title {{
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
  line-height: 1.3;
}}

.task-assignee {{
  font-size: 0.75rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.5rem;
}}

/* View 4: Budgets & Spend Governance */
.budget-overview-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}}

.budget-metric-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 14px;
  padding: 1.25rem;
}}

.progress-track {{
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 9999px;
  margin-top: 0.75rem;
  overflow: hidden;
}}

.progress-fill {{
  height: 100%;
  background: linear-gradient(90deg, var(--accent-gold-dim), var(--accent-gold-bright));
  border-radius: 9999px;
}}

.budget-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}}

.budget-table th {{
  text-align: left;
  padding: 0.75rem 1rem;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-glass);
}}

.budget-table td {{
  padding: 0.85rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}}

/* View 5: Governance & Approvals Queue */
.approval-list {{
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}}

.approval-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 14px;
  padding: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}}

.approval-card.resolved {{
  opacity: 0.6;
  border-color: rgba(255, 255, 255, 0.08);
}}

.approval-info {{ flex: 1; padding-right: 1.5rem; }}

.approval-header {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}}

.approval-type-tag {{
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
  background: rgba(229, 168, 35, 0.15);
  color: var(--accent-gold-bright);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}}

.approval-actions {{
  display: flex;
  gap: 0.65rem;
}}

.btn-approve {{
  background: var(--accent-gold);
  color: #13110E;
  font-weight: 800;
  border: none;
  padding: 0.5rem 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}}

.btn-approve:hover {{
  background: var(--accent-gold-bright);
  box-shadow: 0 0 14px rgba(229, 168, 35, 0.5);
}}

.btn-reject {{
  background: rgba(239, 68, 68, 0.15);
  color: #EF4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  font-weight: 700;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
}}

.btn-reject:hover {{
  background: rgba(239, 68, 68, 0.3);
}}

/* View 6: Harness Options & Connectors */
.settings-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}}

.setting-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 14px;
  padding: 1.5rem;
}}

.setting-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}}

.setting-title {{ font-weight: 700; font-size: 0.9rem; }}
.setting-desc {{ font-size: 0.78rem; color: var(--text-muted); }}

.segmented-control {{
  display: flex;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 8px;
  padding: 0.2rem;
  border: 1px solid var(--border-glass);
}}

.seg-btn {{
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.35rem 0.65rem;
  border-radius: 6px;
  cursor: pointer;
}}

.seg-btn.active {{
  background: var(--accent-gold);
  color: #13110E;
  font-weight: 800;
}}

.connector-badge {{
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--accent-gold-bright);
}}
  </style>
</head>
<body>
  <!-- Top Menu Bar -->
  <div class="hud-menubar">
    <div class="menubar-left">
      <div class="system-brand">
        <svg class="buzburg-bee-icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 26px; height: 26px;">
          <polygon points="32,3 58,18 58,46 32,61 6,46 6,18" stroke="#E5A823" stroke-width="2.5" fill="rgba(35, 29, 25, 0.55)"/>
          <polygon points="18,12 26,22 17,20" fill="#BDB4A8"/>
          <polygon points="12,17 26,26 15,28" fill="#E5A823"/>
          <polygon points="14,27 28,32 18,34" fill="#BDB4A8"/>
          <polygon points="18,34 30,36 22,39" fill="#E5A823"/>
          <path d="M40,16 L43,12 M44,18 L48,15" stroke="#FAF8F5" stroke-width="1.8" stroke-linecap="round"/>
          <polygon points="36,19 43,15 47,19 47,25 41,28 35,24" fill="#FAF8F5"/>
          <polygon points="32,28 42,28 38,36 28,36" fill="#E5A823"/>
          <polygon points="28,37 38,37 36,43 26,43" fill="#362D26" stroke="#E5A823" stroke-width="0.5"/>
          <polygon points="26,44 36,44 31,52" fill="#E5A823"/>
        </svg>
        <span>SWARMOJO <span style="color: var(--accent-gold);">HUD</span></span>
        <span style="color: var(--text-dim); font-weight: 400; font-size: 0.8rem;">// SOVEREIGN-OS</span>
      </div>
      <div>Session: 0x8F94-AEON</div>
      <div>Kernel: Native Mojo v25.1</div>
    </div>
    <div class="menubar-right">
      <button class="btn-heartbeat" onclick="triggerHeartbeat()" title="Wake specialists and execute pulse">
        <span>💓</span> Pulse Heartbeat
      </button>
      <div class="live-indicator"><div class="pulse-dot"></div> HIVE ORCHESTRATOR ONLINE</div>
      <div>MEM: 412 MB / 800 TOKENS</div>
      <div>LATENCY: 12 µs</div>
    </div>
  </div>

  <!-- Subnav Tabs Bar -->
  <div class="hud-subnav">
    <button class="nav-tab active" data-tab="telemetry" onclick="switchTab('telemetry')">
      <span>⚡</span> Live Telemetry
    </button>
    <button class="nav-tab" data-tab="orgchart" onclick="switchTab('orgchart')">
      <span>🏢</span> Swarm Org Chart
    </button>
    <button class="nav-tab" data-tab="tasks" onclick="switchTab('tasks')">
      <span>📋</span> Goals &amp; Tasks
    </button>
    <button class="nav-tab" data-tab="budgets" onclick="switchTab('budgets')">
      <span>💰</span> Budgets &amp; Spend
    </button>
    <button class="nav-tab" data-tab="governance" onclick="switchTab('governance')">
      <span>🛡️</span> Governance &amp; Approvals <span class="badge-counter" id="approvalCount">2</span>
    </button>
    <button class="nav-tab" data-tab="settings" onclick="switchTab('settings')">
      <span>⚙️</span> Harness Options
    </button>
  </div>

  <!-- VIEW 1: Live Telemetry Workspace -->
  <div id="view-telemetry" class="hud-view active">
    <div class="telemetry-layout">
      <!-- Left: Roster -->
      <div class="glass-panel">
        <div class="panel-header">
          <span class="panel-title">👥 SPECIALIST ROSTER</span>
          <span style="font-size: 0.8rem; color: var(--text-dim);">{len(roster)} Agents Active</span>
        </div>
        <div class="panel-body">
          {''.join(roster_cards)}
        </div>
      </div>

      <!-- Center: Telemetry Grid & Terminal -->
      <div class="center-viewport">
        <div class="glass-panel" style="padding: 1.25rem;">
          <div class="telemetry-grid">
            <div class="telemetry-card">
              <span class="telemetry-lbl">SUB-10µs SYMBOL LOOKUPS</span>
              <span class="telemetry-val gold">142,800</span>
              <span class="telemetry-lbl">Symdex In-Memory Speed</span>
            </div>
            <div class="telemetry-card">
              <span class="telemetry-lbl">PARALLEL CONCURRENCY</span>
              <span class="telemetry-val ivory">99.98%</span>
              <span class="telemetry-lbl">StateFresh OCC Collision-Free</span>
            </div>
            <div class="telemetry-card">
              <span class="telemetry-lbl">ANGULAR TRAJECTORY DRIFT</span>
              <span class="telemetry-val amber">4.2°</span>
              <span class="telemetry-lbl">Target Threshold &lt; 65°</span>
            </div>
          </div>
        </div>

        <div class="glass-panel">
          <div class="panel-header">
            <span class="panel-title">⚡ REAL-TIME HARNESS PIPELINE</span>
            <span style="font-size: 0.8rem; color: var(--accent-gold);">TriggerTangle Offline Rehearsal</span>
          </div>
          <div class="panel-body">
            <div class="live-terminal" id="terminalOutput">
[00:00:01.004] [AtlasCoordinator] Objective received: Multi-agent studio &amp; coding convergence.
[00:00:01.018] [FastgateTriage] 256-dim phase vector router mapped tools in 18 µs.
[00:00:01.042] [DaedalusArchitect] Pi exact substring edit committed with Rewind snapshot #snap-482.
[00:00:01.065] [VitruviusDesign] Buzburg honey-gold glassmorphism theme compiled with Impeccable contrast floor.
[00:00:01.092] [LumiereStudio] Diffusion Flux graph exported for 16:9 4K render.
[00:00:01.115] [OrwellScribe] Ghost Protocol passed: 0 banned clichés, sentence variance = 8.4.
[00:00:01.128] [MojoDrift] Angular trajectory: 4.2° (SAFE &lt; 65°). Status: VERIFIED.
            </div>
          </div>
        </div>
      </div>

      <!-- Right: DAG -->
      <div class="glass-panel">
        <div class="panel-header">
          <span class="panel-title">🕸️ ACTIVE TASK DAG</span>
          <span style="font-size: 0.8rem; color: var(--accent-gold);">Verified WorkflowProof</span>
        </div>
        <div class="panel-body">
          {''.join(dag_items)}
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 2: Swarm Org Chart -->
  <div id="view-orgchart" class="hud-view">
    <div class="panel-header" style="margin-bottom: 1rem; border-radius: 12px; background: var(--bg-glass); border: 1px solid var(--border-glass);">
      <div>
        <span class="panel-title">🏢 SWARM ORGANIZATIONAL HIERARCHY</span>
        <span style="font-size: 0.8rem; color: var(--text-muted);">Executive reporting lines, specialist tiers, and governance structure</span>
      </div>
      <button class="btn-heartbeat" onclick="alert('Hire Specialist: Specify Agent ID, Role, Model, and Budget Cap.')">+ Hire Specialist</button>
    </div>
    <div class="org-container">
      <!-- Tier 1: Executive Lead -->
      <div class="org-level">
        <div class="org-card" style="border-color: var(--accent-gold);">
          <span class="org-tier-tag">Executive</span>
          <div class="org-card-header">
            <div class="org-card-avatar">⚡</div>
            <div>
              <div class="org-card-name">Atlas</div>
              <div class="org-card-role">Swarm Coordinator &amp; Executive Lead</div>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--accent-gold);">Model: deepseek-r1 • Reports to User / Board</div>
          <div class="org-card-stats">
            <span>Spend: $14.20 / $80</span>
            <span style="color: var(--accent-emerald);">● ACTIVE</span>
          </div>
        </div>
      </div>

      <!-- Tier 2: Specialists & Leads -->
      <div class="org-level">
        <div class="org-card">
          <span class="org-tier-tag">Lead</span>
          <div class="org-card-header">
            <div class="org-card-avatar">🛠️</div>
            <div>
              <div class="org-card-name">Daedalus</div>
              <div class="org-card-role">Principal DeepCode Architect</div>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Model: qwen-coder • Reports to Atlas</div>
          <div class="org-card-stats">
            <span>Spend: $28.50 / $60</span>
            <span style="color: #F59E0B;">● BUSY</span>
          </div>
        </div>

        <div class="org-card">
          <span class="org-tier-tag">Specialist</span>
          <div class="org-card-header">
            <div class="org-card-avatar">🎨</div>
            <div>
              <div class="org-card-name">Vitruvius</div>
              <div class="org-card-role">Staff UI/UX Systems Designer</div>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Model: qwen-coder • Reports to Daedalus</div>
          <div class="org-card-stats">
            <span>Spend: $6.15 / $40</span>
            <span style="color: var(--text-muted);">● IDLE</span>
          </div>
        </div>

        <div class="org-card">
          <span class="org-tier-tag">Specialist</span>
          <div class="org-card-header">
            <div class="org-card-avatar">🎬</div>
            <div>
              <div class="org-card-name">Lumiere</div>
              <div class="org-card-role">Studio Director &amp; Multimodal</div>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Model: flux-dev • Reports to Atlas</div>
          <div class="org-card-stats">
            <span>Spend: $19.40 / $50</span>
            <span style="color: #F59E0B;">● RENDERING</span>
          </div>
        </div>

        <div class="org-card">
          <span class="org-tier-tag">Specialist</span>
          <div class="org-card-header">
            <div class="org-card-avatar">✍️</div>
            <div>
              <div class="org-card-name">Orwell</div>
              <div class="org-card-role">Lead Ghost Scribe &amp; Writer</div>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Model: qwen-coder • Reports to Atlas</div>
          <div class="org-card-stats">
            <span>Spend: $4.80 / $30</span>
            <span style="color: var(--accent-emerald);">● ACTIVE</span>
          </div>
        </div>

        <div class="org-card">
          <span class="org-tier-tag">Auditor</span>
          <div class="org-card-header">
            <div class="org-card-avatar">🛡️</div>
            <div>
              <div class="org-card-name">Aegis</div>
              <div class="org-card-role">Chief Security Auditor</div>
            </div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Model: llama3 • Autonomous Constitutional Guard</div>
          <div class="org-card-stats">
            <span>Spend: $5.20 / $40</span>
            <span style="color: var(--accent-gold);">● MONITORING</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 3: Goals & Tasks Kanban -->
  <div id="view-tasks" class="hud-view">
    <div class="panel-header" style="margin-bottom: 1rem; border-radius: 12px; background: var(--bg-glass); border: 1px solid var(--border-glass);">
      <div>
        <span class="panel-title">📋 GOALS &amp; ISSUES KANBAN BOARD</span>
        <span style="font-size: 0.8rem; color: var(--text-muted);">Autonomous delegation, dependencies, and execution milestones</span>
      </div>
      <button class="btn-heartbeat" onclick="alert('New Task: Enter Title, Assignee, Priority, and Blocking Issue ID.')">+ New Task Issue</button>
    </div>
    <div class="kanban-board">
      <!-- Col 1: Backlog -->
      <div class="kanban-col">
        <div class="kanban-col-header"><span>Backlog</span> <span>1</span></div>
        <div class="kanban-col-body">
          <div class="kanban-card">
            <div class="kanban-card-top">
              <span class="task-id">TASK-105</span>
              <span class="task-priority medium">Medium</span>
            </div>
            <div class="task-title">Ghost Protocol Cadence Polish</div>
            <div style="font-size: 0.75rem; color: var(--text-dim);">Audit docs for banned AI clichés and ensure sentence cadence variance &gt; 7.0.</div>
            <div class="task-assignee"><span>✍️</span> Orwell</div>
          </div>
        </div>
      </div>

      <!-- Col 2: In Progress -->
      <div class="kanban-col">
        <div class="kanban-col-header"><span>In Progress</span> <span>2</span></div>
        <div class="kanban-col-body">
          <div class="kanban-card">
            <div class="kanban-card-top">
              <span class="task-id">TASK-102</span>
              <span class="task-priority critical">Critical</span>
            </div>
            <div class="task-title">Sub-10µs Symdex In-Memory Warmup</div>
            <div style="font-size: 0.75rem; color: var(--text-dim);">Preload syntax graph for fastgate triage in native Mojo kernel.</div>
            <div class="task-assignee"><span>🛠️</span> Daedalus</div>
          </div>
          <div class="kanban-card">
            <div class="kanban-card-top">
              <span class="task-id">TASK-103</span>
              <span class="task-priority high">High</span>
            </div>
            <div class="task-title">Audit Path Traversal on Device Names</div>
            <div style="font-size: 0.75rem; color: var(--text-dim);">Run PathSentry checks on COM1, LPT1, and AUX device names.</div>
            <div class="task-assignee"><span>🛡️</span> Aegis</div>
          </div>
        </div>
      </div>

      <!-- Col 3: Blocked -->
      <div class="kanban-col">
        <div class="kanban-col-header"><span style="color: #EF4444;">Blocked</span> <span>1</span></div>
        <div class="kanban-col-body">
          <div class="kanban-card" style="border-color: rgba(239, 68, 68, 0.4);">
            <div class="kanban-card-top">
              <span class="task-id">TASK-106</span>
              <span class="task-priority critical">Critical</span>
            </div>
            <div class="task-title">StateFresh Distributed File Lease OCC</div>
            <div style="font-size: 0.75rem; color: #EF4444;">⚠️ Blocked by TASK-102 (Symdex Warmup)</div>
            <div class="task-assignee"><span>🛠️</span> Daedalus</div>
          </div>
        </div>
      </div>

      <!-- Col 4: Review -->
      <div class="kanban-col">
        <div class="kanban-col-header"><span>Review</span> <span>1</span></div>
        <div class="kanban-col-body">
          <div class="kanban-card">
            <div class="kanban-card-top">
              <span class="task-id">TASK-104</span>
              <span class="task-priority medium">Medium</span>
            </div>
            <div class="task-title">4K 16:9 Studio Banner Reel</div>
            <div style="font-size: 0.75rem; color: var(--text-dim);">Render diffusion keyframes for multimodal release assets.</div>
            <div class="task-assignee"><span>🎬</span> Lumiere</div>
          </div>
        </div>
      </div>

      <!-- Col 5: Done -->
      <div class="kanban-col">
        <div class="kanban-col-header"><span style="color: var(--accent-emerald);">Done</span> <span>1</span></div>
        <div class="kanban-col-body">
          <div class="kanban-card">
            <div class="kanban-card-top">
              <span class="task-id">TASK-101</span>
              <span class="task-priority high">High</span>
            </div>
            <div class="task-title">Swarmojo HUD Hive UI Unification</div>
            <div style="font-size: 0.75rem; color: var(--text-dim);">Align HUD themes and brand tokens with Buzburg honey gold and charcoal.</div>
            <div class="task-assignee"><span>🎨</span> Vitruvius</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 4: Budgets & Spend Governance -->
  <div id="view-budgets" class="hud-view">
    <div class="budget-overview-grid">
      <div class="budget-metric-card">
        <div style="font-size: 0.8rem; color: var(--text-muted);">TOTAL ORGANIZATION SPEND</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: var(--accent-gold-bright); margin-top: 0.25rem;">$78.25 <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 400;">/ $250.00 Hard Cap</span></div>
        <div class="progress-track"><div class="progress-fill" style="width: 31.3%;"></div></div>
        <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 0.4rem;">31.3% of allocated organization budget consumed</div>
      </div>

      <div class="budget-metric-card">
        <div style="font-size: 0.8rem; color: var(--text-muted);">TOTAL TOKENS CONSUMED</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: var(--text-main); margin-top: 0.25rem;">4.33M <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 400;">/ 18.0M Limit</span></div>
        <div class="progress-track"><div class="progress-fill" style="width: 24.1%;"></div></div>
        <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 0.4rem;">Avg prompt cost: $0.000018 / 1k tokens</div>
      </div>

      <div class="budget-metric-card">
        <div style="font-size: 0.8rem; color: var(--text-muted);">RUNAWAY LOOP CIRCUIT BREAKER</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: var(--accent-emerald); margin-top: 0.25rem;">ACTIVE <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 400;">(Safe)</span></div>
        <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 0.8rem;">Auto-kills recursive agent loops exceeding 15 iterative turns</div>
      </div>
    </div>

    <div class="glass-panel" style="flex: 1;">
      <div class="panel-header">
        <span class="panel-title">💰 PER-AGENT BUDGET &amp; TOKEN ALLOCATION</span>
        <button class="btn-heartbeat" onclick="alert('Budgets reset to baseline limits.')">Reset Spend Counters</button>
      </div>
      <div style="overflow-y: auto; flex: 1; padding: 0.5rem 1rem;">
        <table class="budget-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th>Role</th>
              <th>Current Spend</th>
              <th>Cap</th>
              <th>Utilization</th>
              <th>Tokens Used</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>⚡ Atlas</strong></td>
              <td>Executive Coordinator</td>
              <td style="color: var(--accent-gold); font-weight: 700;">$14.20</td>
              <td>$80.00</td>
              <td><div class="progress-track" style="width: 120px;"><div class="progress-fill" style="width: 17.8%;"></div></div></td>
              <td>720,000</td>
              <td><span class="agent-badge active">NORMAL</span></td>
            </tr>
            <tr>
              <td><strong>🛠️ Daedalus</strong></td>
              <td>Principal DeepCode Architect</td>
              <td style="color: var(--accent-gold); font-weight: 700;">$28.50</td>
              <td>$60.00</td>
              <td><div class="progress-track" style="width: 120px;"><div class="progress-fill" style="width: 47.5%;"></div></div></td>
              <td>1,850,000</td>
              <td><span class="agent-badge busy">NORMAL</span></td>
            </tr>
            <tr>
              <td><strong>🎨 Vitruvius</strong></td>
              <td>Staff UI/UX Designer</td>
              <td style="color: var(--accent-gold); font-weight: 700;">$6.15</td>
              <td>$40.00</td>
              <td><div class="progress-track" style="width: 120px;"><div class="progress-fill" style="width: 15.4%;"></div></div></td>
              <td>310,000</td>
              <td><span class="agent-badge idle">NORMAL</span></td>
            </tr>
            <tr>
              <td><strong>🎬 Lumiere</strong></td>
              <td>Studio Director</td>
              <td style="color: var(--accent-gold); font-weight: 700;">$19.40</td>
              <td>$50.00</td>
              <td><div class="progress-track" style="width: 120px;"><div class="progress-fill" style="width: 38.8%;"></div></div></td>
              <td>950,000</td>
              <td><span class="agent-badge busy">NORMAL</span></td>
            </tr>
            <tr>
              <td><strong>✍️ Orwell</strong></td>
              <td>Lead Ghost Scribe</td>
              <td style="color: var(--accent-gold); font-weight: 700;">$4.80</td>
              <td>$30.00</td>
              <td><div class="progress-track" style="width: 120px;"><div class="progress-fill" style="width: 16.0%;"></div></div></td>
              <td>240,000</td>
              <td><span class="agent-badge active">NORMAL</span></td>
            </tr>
            <tr>
              <td><strong>🛡️ Aegis</strong></td>
              <td>Chief Security Auditor</td>
              <td style="color: var(--accent-gold); font-weight: 700;">$5.20</td>
              <td>$40.00</td>
              <td><div class="progress-track" style="width: 120px;"><div class="progress-fill" style="width: 13.0%;"></div></div></td>
              <td>260,000</td>
              <td><span class="agent-badge active">NORMAL</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- VIEW 5: Governance & Approvals Queue -->
  <div id="view-governance" class="hud-view">
    <div class="panel-header" style="margin-bottom: 1.5rem; border-radius: 12px; background: var(--bg-glass); border: 1px solid var(--border-glass);">
      <div>
        <span class="panel-title">🛡️ HUMAN-IN-THE-LOOP AUTHORIZATION QUEUE</span>
        <span style="font-size: 0.8rem; color: var(--text-muted);">High-stakes actions gated by constitutional security rules</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--accent-gold);">Zero-bypass policy active</div>
    </div>

    <div class="approval-list">
      <!-- Item 1: Git Push -->
      <div class="approval-card" id="card-APPR-401">
        <div class="approval-info">
          <div class="approval-header">
            <span class="approval-type-tag">git_push</span>
            <span style="font-weight: 700;">Push release commits directly to origin/main</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.4rem;">Requested by <strong>🛠️ Daedalus</strong> (Principal Architect)</div>
          <div style="font-size: 0.75rem; color: var(--text-dim); background: rgba(0, 0, 0, 0.4); padding: 0.4rem 0.6rem; border-radius: 6px;">
            Target: <code>https://github.com/Buzburg/Swarmojo.git (branch: main)</code> • Commits: 3 • Verified: WorkflowProof #VP-892
          </div>
        </div>
        <div class="approval-actions" id="actions-APPR-401">
          <button class="btn-approve" onclick="resolveApproval('APPR-401', 'Approved git push to origin/main.')">✓ Approve Push</button>
          <button class="btn-reject" onclick="resolveApproval('APPR-401', 'Rejected by administrator.', false)">✗ Reject</button>
        </div>
      </div>

      <!-- Item 2: GPU Cloud Spend -->
      <div class="approval-card" id="card-APPR-402">
        <div class="approval-info">
          <div class="approval-header">
            <span class="approval-type-tag">api_spend</span>
            <span style="font-weight: 700;">Allocate $15.00 GPU cloud burst for 60s video diffusion render</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.4rem;">Requested by <strong>🎬 Lumiere</strong> (Studio Director)</div>
          <div style="font-size: 0.75rem; color: var(--text-dim); background: rgba(0, 0, 0, 0.4); padding: 0.4rem 0.6rem; border-radius: 6px;">
            Provider: Flux-Dev-Cloud • Spend: $15.00 USD • Resolution: 3840x2160 (4K 60fps)
          </div>
        </div>
        <div class="approval-actions" id="actions-APPR-402">
          <button class="btn-approve" onclick="resolveApproval('APPR-402', 'Approved $15.00 GPU spend.')">✓ Approve Spend</button>
          <button class="btn-reject" onclick="resolveApproval('APPR-402', 'Rejected budget allocation.', false)">✗ Reject</button>
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 6: Harness Options & Connectors -->
  <div id="view-settings" class="hud-view">
    <div class="settings-grid">
      <!-- Card 1: Scheduling & Concurrency -->
      <div class="setting-card">
        <div class="panel-title" style="margin-bottom: 1rem;">⚙️ HARNESS SCHEDULER &amp; EXECUTION</div>
        <div class="setting-row">
          <div>
            <div class="setting-title">Heartbeat Frequency</div>
            <div class="setting-desc">Interval at which dormant specialists wake to check blockers</div>
          </div>
          <div class="segmented-control">
            <button class="seg-btn" onclick="selectSeg(this)">30s</button>
            <button class="seg-btn active" onclick="selectSeg(this)">60s</button>
            <button class="seg-btn" onclick="selectSeg(this)">5m</button>
            <button class="seg-btn" onclick="selectSeg(this)">Manual</button>
          </div>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-title">Concurrency Engine</div>
            <div class="setting-desc">Conflict resolution protocol for parallel file edits</div>
          </div>
          <div class="segmented-control">
            <button class="seg-btn active" onclick="selectSeg(this)">StateFresh OCC</button>
            <button class="seg-btn" onclick="selectSeg(this)">Strict Mutex</button>
          </div>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-title">Auto-Rollback on Failure</div>
            <div class="setting-desc">Instantly restore previous Rewind snapshot on test breakage</div>
          </div>
          <span style="color: var(--accent-emerald); font-weight: 700; font-size: 0.8rem;">ENABLED</span>
        </div>

        <div class="setting-row" style="border-bottom: none;">
          <div>
            <div class="setting-title">PathSentry Device Guard</div>
            <div class="setting-desc">Block Windows reserved device path traversal (COM/AUX/LPT)</div>
          </div>
          <span style="color: var(--accent-emerald); font-weight: 700; font-size: 0.8rem;">ACTIVE</span>
        </div>
      </div>

      <!-- Card 2: BYOA Connectors -->
      <div class="setting-card">
        <div class="panel-title" style="margin-bottom: 1rem;">🔌 BRING YOUR OWN AGENT (BYOA) CONNECTORS</div>
        <div class="setting-row">
          <div>
            <div class="setting-title">Native Mojo v25.1 Kernel</div>
            <div class="setting-desc">Sub-10µs symbol lookup and vector math acceleration</div>
          </div>
          <div class="connector-badge"><div class="pulse-dot"></div> ACTIVE</div>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-title">Claude Code CLI Adapter</div>
            <div class="setting-desc">External CLI worker bridge at <code>http://localhost:5210/agent</code></div>
          </div>
          <div class="connector-badge"><div class="pulse-dot"></div> CONNECTED</div>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-title">OpenCode Subagent Bridge</div>
            <div class="setting-desc">Multi-file refactoring adapter at <code>http://localhost:5211/agent</code></div>
          </div>
          <div class="connector-badge"><div class="pulse-dot"></div> CONNECTED</div>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-title">Ollama Local Inference</div>
            <div class="setting-desc">Air-gapped offline model endpoint at <code>http://localhost:11434</code></div>
          </div>
          <div class="connector-badge"><div class="pulse-dot"></div> READY</div>
        </div>

        <div class="setting-row" style="border-bottom: none;">
          <div>
            <div class="setting-title">Codex Engine Bridge</div>
            <div class="setting-desc">Sandboxed test generation endpoint at <code>http://localhost:5212</code></div>
          </div>
          <div class="connector-badge"><div class="pulse-dot"></div> CONNECTED</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Tab switching
    function switchTab(tabId) {{
      document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
      const activeBtn = document.querySelector(`.nav-tab[data-tab="${{tabId}}"]`);
      if (activeBtn) activeBtn.classList.add('active');

      document.querySelectorAll('.hud-view').forEach(v => v.classList.remove('active'));
      const targetView = document.getElementById('view-' + tabId);
      if (targetView) targetView.classList.add('active');
    }}

    // Heartbeat pulse trigger
    function triggerHeartbeat() {{
      const btn = document.querySelector('.btn-heartbeat');
      btn.style.transform = 'scale(0.95)';
      setTimeout(() => btn.style.transform = 'scale(1)', 150);

      const term = document.getElementById('terminalOutput');
      if (term) {{
        const now = new Date().toISOString().substring(11, 23);
        const log = `\\n[${{now}}] [HeartbeatPulse] Broadcast dispatched to 6 active specialists in 8 µs. All blocker states refreshed.`;
        term.innerText += log;
        term.scrollTop = term.scrollHeight;
      }}
    }}

    // Approval resolution
    function resolveApproval(itemId, message, approved = true) {{
      const card = document.getElementById('card-' + itemId);
      const actions = document.getElementById('actions-' + itemId);
      if (card && actions) {{
        card.classList.add('resolved');
        const color = approved ? 'var(--accent-emerald)' : '#EF4444';
        const label = approved ? '✓ AUTHORIZED' : '✗ REJECTED';
        actions.innerHTML = `<span style="font-weight: 800; font-size: 0.85rem; color: ${{color}};">${{label}}</span>`;
      }}

      // Decrement counter
      const counter = document.getElementById('approvalCount');
      if (counter) {{
        let count = parseInt(counter.innerText) || 0;
        if (count > 0) count--;
        counter.innerText = count;
        if (count === 0) counter.style.display = 'none';
      }}

      // Log to terminal
      const term = document.getElementById('terminalOutput');
      if (term) {{
        const now = new Date().toISOString().substring(11, 23);
        term.innerText += `\\n[${{now}}] [Governance] ${{itemId}} ${{message}} Action resolved by HumanAdmin.`;
        term.scrollTop = term.scrollHeight;
      }}
    }}

    // Segmented control toggle
    function selectSeg(btn) {{
      const parent = btn.parentElement;
      parent.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }}
  </script>
</body>
</html>
"""

        # Write to primary swarmojo_hud.html and alias herald_hud.html for compatibility
        out_file = self.output_dir / "swarmojo_hud.html"
        out_file.write_text(hud_html, encoding="utf-8")
        legacy_file = self.output_dir / "herald_hud.html"
        legacy_file.write_text(hud_html, encoding="utf-8")

        return {
            "status": "ready",
            "file": str(out_file),
            "legacy_file": str(legacy_file),
            "system_title": system_title,
            "total_agents": len(roster),
            "total_milestones": len(milestones),
            "html_length": len(hud_html),
        }

    def build_herald_hud(
        self,
        system_title: str = "Swarmojo HUD",
        agents_roster: Optional[List[Dict[str, Any]]] = None,
        live_dag_milestones: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible alias for build_swarmojo_hud."""
        return self.build_swarmojo_hud(
            system_title=system_title,
            agents_roster=agents_roster,
            live_dag_milestones=live_dag_milestones,
        )


# -------------------------------------------------------------------------
# Visual Canvas Engine & Optical Glass Material System
# -------------------------------------------------------------------------

@dataclass
class CanvasLayer:
    layer_id: str
    name: str
    kind: str             # "background", "vector", "typography", "asset", "filter", "overlay"
    x: int
    y: int
    width: int
    height: int
    opacity: float = 1.0  # [0.0, 1.0]
    blend_mode: str = "normal"  # "normal", "multiply", "screen", "overlay", "soft_light"
    z_index: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OpticalGlassMaterial:
    """Optical glassmorphism material specifications with dynamic refraction."""
    blur_px: int = 24
    transparency: float = 0.65
    refraction_index: float = 1.48
    specular_highlight: str = "rgba(255, 255, 255, 0.15)"
    surface_tint: str = "rgba(17, 24, 39, 0.70)"
    border_glow: str = "1px solid rgba(255, 255, 255, 0.12)"
    shadow_profile: str = "0 8px 32px 0 rgba(0, 0, 0, 0.37)"

    def to_css(self, class_name: str = "optical-glass") -> str:
        return f"""
.{class_name} {{
  background: {self.surface_tint};
  backdrop-filter: blur({self.blur_px}px) saturate(180%);
  -webkit-backdrop-filter: blur({self.blur_px}px) saturate(180%);
  border: {self.border_glow};
  box-shadow: {self.shadow_profile}, inset 0 1px 1px 0 {self.specular_highlight};
  border-radius: 16px;
}}
"""


# Backward-compatible alias
LiquidGlassMaterial = OpticalGlassMaterial


class VisualCanvasEngine:
    """Layered digital canvas composer for UI assets, app icons, and marketing layouts."""

    PRESETS = {
        "app_icon": (1024, 1024, "iOS / macOS / Android Application Icon"),
        "social_banner": (1200, 630, "OpenGraph Social Preview Banner"),
        "hero_canvas": (1920, 1080, "High-Resolution 16:9 Hero Canvas"),
        "card_asset": (800, 1000, "Vertical Product / Card Visual"),
    }

    def __init__(self, output_dir: str | Path = "workspace_design"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.layers: List[CanvasLayer] = []

    def create_canvas(self, preset: str = "hero_canvas", custom_dimensions: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        w, h, desc = (custom_dimensions[0], custom_dimensions[1], "Custom Canvas") if custom_dimensions else self.PRESETS.get(preset, (1920, 1080, "Default"))
        self.layers = [
            CanvasLayer(
                layer_id="layer_bg",
                name="Deep Canvas Background",
                kind="background",
                x=0,
                y=0,
                width=w,
                height=h,
                blend_mode="normal",
                z_index=0,
                properties={"fill": "#0B0F19", "gradient": "linear-gradient(135deg, #0B0F19 0%, #111827 100%)"},
            )
        ]
        return {"preset": preset, "width": w, "height": h, "description": desc, "layers": len(self.layers)}

    def add_layer(
        self,
        name: str,
        kind: str,
        x: int,
        y: int,
        width: int,
        height: int,
        blend_mode: str = "normal",
        opacity: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> CanvasLayer:
        layer = CanvasLayer(
            layer_id=f"layer_{len(self.layers) + 1}",
            name=name,
            kind=kind,
            x=x,
            y=y,
            width=width,
            height=height,
            opacity=opacity,
            blend_mode=blend_mode,
            z_index=len(self.layers),
            properties=properties or {},
        )
        self.layers.append(layer)
        return layer

    def export_spec(self, title: str = "Visual Canvas Spec") -> Dict[str, Any]:
        return {
            "title": title,
            "total_layers": len(self.layers),
            "layers": [l.to_dict() for l in sorted(self.layers, key=lambda l: l.z_index)],
        }


# Backward-compatible alias
PhotocraftCanvasEngine = VisualCanvasEngine

