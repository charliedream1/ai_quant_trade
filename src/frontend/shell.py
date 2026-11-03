"""Persistent Gradio workspace shell for independently mounted modules."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import gradio as gr
from src.core.config import get_settings
from src.notifications.config import config as notification_config

from .common.components import supports_parameter
from .common.navigation import navigation_config
from .header import external_links_html
from .icons import module_icon
from .registry import MODULES
from .theme import gradio_mount_options, theme, theme_runtime_js

SHELL_CACHE_LIMIT = 3

SHELL_CSS = """
:root {
  --shell-brand: #2563eb;
  --shell-ink: #152b3a;
  --shell-muted: #627786;
  --shell-line: #d8e7f3;
  --shell-canvas: #edf6fc;
  color-scheme: light;
}
html, body { min-height: 100%; background: var(--shell-canvas) !important; }
body { margin: 0 !important; }
.gradio-container {
  width: 100% !important;
  max-width: none !important;
  min-height: 100vh !important;
  padding: 0 !important;
  margin: 0 !important;
  background: var(--shell-canvas) !important;
}
.gradio-container main.app,
.gradio-container .contain { width: 100% !important; max-width: none !important; padding: 0 !important; }
#workspace-shell-root { padding: 0 !important; border: 0 !important; background: transparent !important; }
.workspace-shell { min-height: 100vh; display: grid; grid-template-rows: 58px minmax(0, 1fr); color: var(--shell-ink); }
.workspace-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  min-height: 58px;
  padding: 0 16px;
  border-bottom: 1px solid #cbdfea;
  background: rgba(248, 252, 255, .97);
  box-shadow: 0 5px 18px rgba(33, 77, 105, .08);
}
.workspace-brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.workspace-brand img { width: 34px; height: 34px; border-radius: 7px; object-fit: cover; border: 1px solid #bed8e9; }
.workspace-brand-copy { min-width: 0; }
.workspace-brand strong { display: block; color: #12304a; font-size: 16px; line-height: 1.15; }
.workspace-brand span { display: block; margin-top: 2px; color: var(--shell-muted); font-size: 11px; white-space: nowrap; }
.workspace-actions { display: flex; align-items: center; gap: 7px; }
.workspace-market {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid #c4dbea;
  border-radius: 6px;
  background: #fff;
}
.workspace-market button,
.workspace-icon-button {
  min-height: 32px;
  border: 0;
  color: #34556a;
  background: #fff;
  cursor: pointer;
  font: inherit;
}
.workspace-market button { min-width: 45px; padding: 0 9px; font-size: 12px; font-weight: 700; }
.workspace-market button + button { border-left: 1px solid #d7e6ef; }
.workspace-market button.active { color: #fff; background: var(--shell-brand); }
.workspace-icon-button {
  display: inline-grid;
  place-items: center;
  width: 34px;
  padding: 0;
  border: 1px solid #c4dbea;
  border-radius: 6px;
}
.workspace-icon-button:hover { color: var(--shell-brand); border-color: #79afe0; background: #eef7ff; }
.workspace-icon-button svg { width: 16px; height: 16px; }
.workspace-language-button { width: auto; grid-auto-flow: column; gap: 4px; padding: 0 8px; font-size: 11px; }
.workspace-theme-button { width: auto; grid-auto-flow: column; gap: 4px; padding: 0 8px; font-size: 11px; }
.workspace-body { min-height: 0; display: grid; grid-template-columns: 204px minmax(0, 1fr); }
.workspace-sidebar {
  position: relative;
  padding: 12px 9px;
  border-right: 1px solid #ccdfeb;
  background: #f7fbfe;
  transition: width .2s ease, padding .2s ease, background .2s ease;
}
.workspace-shell.sidebar-collapsed .workspace-body { grid-template-columns: 68px minmax(0, 1fr); }
.workspace-shell.sidebar-collapsed .workspace-sidebar { padding: 12px 8px; }
.workspace-shell.sidebar-collapsed .workspace-nav-copy,
.workspace-shell.sidebar-collapsed .workspace-subnav { display: none !important; }
.workspace-shell.sidebar-collapsed .workspace-nav-button { grid-template-columns: 1fr; justify-items: center; padding: 7px 4px; }
.workspace-shell.sidebar-collapsed .workspace-nav-icon { margin: 0 auto; }
.workspace-sidebar-toggle { position: absolute; top: 10px; right: -13px; z-index: 3; width: 26px; height: 26px; min-height: 26px; padding: 0; border: 1px solid #bdd6e8; border-radius: 50%; color: #2d6086; background: #fff; box-shadow: 0 4px 12px rgba(37, 99, 235, .16); cursor: pointer; }
.workspace-sidebar-toggle:hover { color: #fff; background: #2563eb; }
.workspace-nav { display: grid; gap: 3px; }
.workspace-nav-group { display: grid; gap: 3px; }
.workspace-nav-button {
  display: grid;
  grid-template-columns: 25px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 42px;
  padding: 7px 9px;
  border: 1px solid transparent;
  border-radius: 6px;
  color: #34505f;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.workspace-nav-button:hover { color: #174b72; border-color: #d0e3ef; background: #eaf4fb; }
.workspace-nav-button.active { color: #fff; border-color: #2563eb; background: #2563eb; }
.workspace-nav-icon { display: grid; place-items: center; width: 24px; height: 24px; font-size: 12px; font-weight: 900; }
.workspace-nav-copy { min-width: 0; }
.workspace-nav-copy strong { display: block; overflow: hidden; font-size: 13px; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
.workspace-nav-copy small { display: block; overflow: hidden; margin-top: 2px; font-size: 10px; line-height: 1.2; opacity: .72; text-overflow: ellipsis; white-space: nowrap; }
.workspace-subnav {
  display: none;
  gap: 2px;
  margin: 1px 0 5px 32px;
  padding-left: 8px;
  border-left: 2px solid #c8def0;
}
.workspace-nav-group.active .workspace-subnav { display: grid; }
.workspace-subnav-button {
  min-height: 30px;
  padding: 5px 8px;
  border: 0;
  border-radius: 4px;
  color: #526b7a;
  background: transparent;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.workspace-subnav-button:hover { color: #174b72; background: #eaf4fb; }
.workspace-subnav-button.active { color: #1d4ed8; background: #dceeff; }
.workspace-main { position: relative; min-width: 0; min-height: 0; background: #edf6fc; }
.workspace-frame-status {
  position: absolute;
  inset: 14px auto auto 50%;
  z-index: 4;
  transform: translateX(-50%);
  padding: 7px 11px;
  border: 1px solid #c5ddea;
  border-radius: 6px;
  color: #3b596b;
  background: rgba(255, 255, 255, .96);
  box-shadow: 0 8px 20px rgba(28, 70, 96, .12);
  font-size: 12px;
}
.workspace-frame-status[hidden] { display: none; }
.workspace-frame-host { width: 100%; height: calc(100vh - 58px); min-height: 620px; }
.workspace-frame {
  display: none;
  width: 100%;
  height: 100%;
  border: 0;
  background: #edf6fc;
}
.workspace-frame.active { display: block; }
@media (max-width: 880px) {
  .workspace-shell { grid-template-rows: auto minmax(0, 1fr); }
  .workspace-topbar { position: relative; min-height: 54px; padding: 8px 10px; }
  .workspace-brand span { display: none; }
  .workspace-body { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
  .workspace-sidebar { overflow-x: auto; padding: 7px; border-right: 0; border-bottom: 1px solid #ccdfeb; }
  .workspace-sidebar-toggle { display: none; }
  .workspace-nav { display: flex; width: max-content; }
  .workspace-nav-group { display: flex; }
  .workspace-nav-group.active .workspace-subnav { display: flex; }
  .workspace-nav-button { width: auto; min-width: 92px; min-height: 38px; grid-template-columns: 20px auto; padding: 6px 8px; }
  .workspace-nav-copy small { display: none; }
  .workspace-subnav { margin: 0 3px; padding: 3px; border: 0; align-items: center; }
  .workspace-subnav-button { white-space: nowrap; }
  .workspace-frame-host { height: calc(100vh - 109px); min-height: 560px; }
}
@media (max-width: 520px) {
  .workspace-brand strong { font-size: 14px; }
  .workspace-market { display: none; }
.workspace-nav-button { min-width: 84px; }
}
@media (max-width: 880px) {
  .workspace-body { grid-template-columns: minmax(0, 1fr) !important; grid-template-rows: auto minmax(0, 1fr) !important; }
  .workspace-sidebar { overflow-x: auto; padding: 7px; border-right: 0; border-bottom: 1px solid var(--shell-line); }
  .workspace-nav { display: flex; width: max-content; }
  .workspace-nav-group { display: flex; }
  .workspace-nav-group.active .workspace-subnav { display: flex; }
  .workspace-nav-button { width: auto; min-width: 92px; min-height: 38px; grid-template-columns: 20px auto; padding: 6px 8px; }
  .workspace-nav-copy small { display: none; }
  .workspace-subnav { margin: 0 3px; padding: 3px; border: 0; align-items: center; }
  .workspace-subnav-button { white-space: nowrap; }
  .workspace-main { padding: 8px; }
  .workspace-frame-host { height: calc(100vh - 124px); min-height: 560px; }
}
@media (max-width: 520px) {
  .workspace-main { padding: 0; }
  .workspace-frame-host { height: calc(100vh - 110px); min-height: 560px; border: 0; border-radius: 0; box-shadow: none; }
}
main.app > footer { display: none !important; }
html, body, .gradio-container, main.app { height: 100%; overflow: hidden !important; }
html[data-theme="dark"] .workspace-topbar,
html[data-theme="dark"] .workspace-sidebar { background: #102131 !important; border-color: #2e4961 !important; }
html[data-theme="dark"] body,
html[data-theme="dark"] .gradio-container { background: #0b1724 !important; }
html[data-theme="dark"] .workspace-main,
html[data-theme="dark"] .workspace-frame { background: #0b1724; }
html[data-theme="dark"] .workspace-market,
html[data-theme="dark"] .workspace-icon-button,
html[data-theme="dark"] .workspace-sidebar-toggle { color: #d9eaff; background: #1b3146; border-color: #3d5b75; }
html[data-theme="dark"] .workspace-brand strong { color: #e6eef7 !important; }
html[data-theme="dark"] .workspace-brand span { color: #9fb2c5 !important; }
html[data-theme="dark"] .workspace-nav-button,
html[data-theme="dark"] .workspace-nav-copy strong { color: #c8d8e7 !important; }
html[data-theme="dark"] .workspace-nav-copy small { color: #8fa8bb !important; }
html[data-theme="dark"] .workspace-nav-button:hover { background: #1b3c59; border-color: #4679a1; }
html[data-theme="dark"] .workspace-subnav-button { color: #a9bfd2 !important; }
html[data-theme="dark"] .workspace-subnav-button.active { color: #d9eaff; background: #214a6d; }

/* Product shell skin: quiet chrome, clear hierarchy, and a stronger content frame. */
:root {
  --shell-brand: #5267e8;
  --shell-brand-strong: #3f51c8;
  --shell-ink: #172333;
  --shell-muted: #6b778a;
  --shell-line: #e3e8f0;
  --shell-canvas: #f3f6fa;
  --shell-surface: #ffffff;
  --shell-shadow: 0 1px 2px rgba(24, 35, 51, .05), 0 12px 28px rgba(48, 65, 96, .08);
}
.workspace-shell { font-family: "Inter", "Segoe UI Variable", "Microsoft YaHei", sans-serif; background: var(--shell-canvas); }
.workspace-topbar {
  min-height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid var(--shell-line);
  background: color-mix(in srgb, var(--shell-surface) 90%, var(--shell-canvas)) !important;
  box-shadow: 0 1px 2px rgba(24, 35, 51, .04), 0 10px 26px rgba(48, 65, 96, .07);
}
.workspace-brand { gap: 12px; }
.workspace-brand img { width: 38px; height: 38px; border-radius: 11px; border-color: #d5ddeb; box-shadow: 0 4px 12px rgba(48, 65, 96, .12); }
.workspace-brand strong { color: var(--shell-ink); font-size: 15px; letter-spacing: -.01em; }
.workspace-brand span { color: var(--shell-muted); font-size: 10px; letter-spacing: .04em; }
.workspace-actions { gap: 8px; }
.workspace-market,
.workspace-icon-button { border-color: var(--shell-line); background: var(--shell-surface); box-shadow: 0 1px 2px rgba(24, 35, 51, .04); }
.workspace-market { border-radius: 9px; }
.workspace-market button,
.workspace-icon-button { color: #58657a; background: transparent; }
.workspace-market button { font-size: 11px; }
.workspace-market button.active { color: #fff; background: var(--shell-brand); }
.workspace-icon-button { border-radius: 9px; }
.workspace-icon-button:hover { color: var(--shell-brand-strong); border-color: color-mix(in srgb, var(--shell-brand) 35%, var(--shell-line)); background: color-mix(in srgb, var(--shell-brand) 7%, var(--shell-surface)); box-shadow: var(--shell-shadow); }
.workspace-sidebar { padding: 18px 11px; border-right: 1px solid var(--shell-line); background: color-mix(in srgb, var(--shell-surface) 80%, var(--shell-canvas)); }
.workspace-nav { gap: 5px; }
.workspace-nav-group { gap: 2px; }
.workspace-nav-button { min-height: 44px; padding: 8px 11px; border: 0; border-radius: 10px; color: #647086; font-weight: 600; transition: background .18s ease, color .18s ease, box-shadow .18s ease; }
.workspace-nav-button:hover { color: var(--shell-brand-strong); border: 0; background: color-mix(in srgb, var(--shell-brand) 7%, transparent); box-shadow: none; }
.workspace-nav-button.active { color: var(--shell-brand-strong); border: 0; background: color-mix(in srgb, var(--shell-brand) 11%, var(--shell-surface)); box-shadow: inset 3px 0 0 var(--shell-brand), 0 4px 12px rgba(48, 65, 96, .06); }
.workspace-nav-icon { color: currentColor; font-size: 13px; }
.workspace-nav-copy strong { font-size: 13px; letter-spacing: -.005em; }
.workspace-nav-copy small { margin-top: 3px; color: var(--shell-muted); font-size: 10px; opacity: .9; }
.workspace-subnav { margin: 2px 0 7px 32px; padding: 4px 0 4px 10px; border-left: 1px solid color-mix(in srgb, var(--shell-brand) 25%, var(--shell-line)); }
.workspace-subnav-button { min-height: 32px; padding: 6px 10px; border-radius: 8px; color: var(--shell-muted); font-size: 11px; font-weight: 600; }
.workspace-subnav-button:hover { color: var(--shell-brand-strong); background: color-mix(in srgb, var(--shell-brand) 7%, transparent); }
.workspace-subnav-button.active { color: var(--shell-brand-strong); background: color-mix(in srgb, var(--shell-brand) 13%, var(--shell-surface)); }
.workspace-main { padding: 16px 18px 18px; background: var(--shell-canvas); }
.workspace-frame-host { height: calc(100vh - 98px); min-height: 600px; overflow: hidden; border: 1px solid var(--shell-line); border-radius: 16px; background: var(--shell-surface); box-shadow: var(--shell-shadow); }
.workspace-frame { height: 100%; background: var(--shell-surface); }
.workspace-frame-status { border-color: var(--shell-line); border-radius: 10px; background: var(--shell-surface); box-shadow: var(--shell-shadow); }
.workspace-sidebar-toggle { top: 18px; right: -13px; border-color: var(--shell-line); color: var(--shell-brand-strong); background: var(--shell-surface); box-shadow: var(--shell-shadow); }
.workspace-sidebar-toggle:hover { color: #fff; background: var(--shell-brand); }
html[data-theme="dark"] .workspace-topbar,
html[data-theme="dark"] .workspace-sidebar { background: #0f1c2b !important; border-color: #293b50 !important; }
html[data-theme="dark"] .workspace-main,
html[data-theme="dark"] .workspace-frame-host,
html[data-theme="dark"] .workspace-frame { background: #091522; border-color: #293b50; }
html[data-theme="dark"] .workspace-nav-button { color: #aab8ca !important; }
html[data-theme="dark"] .workspace-nav-button:hover { color: #cbd7e6 !important; background: rgba(127, 145, 238, .12); }
html[data-theme="dark"] .workspace-nav-button.active { color: #e4ebf7 !important; background: rgba(127, 145, 238, .19); box-shadow: inset 3px 0 0 #91a5ff; }
html[data-theme="dark"] .workspace-subnav-button { color: #96a8bc !important; }
html[data-theme="dark"] .workspace-subnav-button.active { color: #e7edfa !important; background: rgba(127, 145, 238, .20); }
html[data-theme="dark"] #quant-workspace-shell {
  --shell-brand: #91a5ff;
  --shell-brand-strong: #b5c2ff;
  --shell-ink: #e9eff8;
  --shell-muted: #a3b0c3;
  --shell-line: #2d3b50;
  --shell-canvas: #091522;
  --shell-surface: #101d2c;
}
html[data-theme="dark"] #quant-workspace-shell .workspace-topbar,
html[data-theme="dark"] #quant-workspace-shell .workspace-sidebar { background: var(--shell-surface) !important; border-color: var(--shell-line) !important; }
html[data-theme="dark"] #quant-workspace-shell .workspace-main,
html[data-theme="dark"] #quant-workspace-shell .workspace-frame-host { background: var(--shell-canvas) !important; border-color: var(--shell-line) !important; }
html[data-theme="dark"] #quant-workspace-shell .workspace-icon-button,
html[data-theme="dark"] #quant-workspace-shell .workspace-market { color: var(--shell-ink) !important; background: var(--shell-surface) !important; border-color: var(--shell-line) !important; }
html[data-theme="dark"] #quant-workspace-shell .workspace-market button { color: var(--shell-ink) !important; }
html[data-theme="dark"] #quant-workspace-shell .workspace-actions button * { color: inherit !important; -webkit-text-fill-color: currentColor !important; }
html[data-theme="dark"] #quant-workspace-shell .workspace-brand strong,
html[data-theme="dark"] #quant-workspace-shell .workspace-nav-copy strong { color: var(--shell-ink) !important; }
html[data-theme="dark"] #quant-workspace-shell .workspace-subnav-button.active { color: var(--shell-ink) !important; background: #263455 !important; }
@media (max-width: 880px) {
  .workspace-topbar { min-height: 58px; padding: 8px 10px; }
  .workspace-main { padding: 8px; }
  .workspace-frame-host { height: calc(100vh - 124px); min-height: 560px; border-radius: 13px; }
  .workspace-sidebar { padding: 7px; }
}
@media (max-width: 520px) {
  .workspace-main { padding: 0; }
  .workspace-frame-host { height: calc(100vh - 110px); min-height: 560px; border: 0; border-radius: 0; box-shadow: none; }
}
@media (max-width: 880px) {
  .workspace-body { grid-template-columns: minmax(0, 1fr) !important; grid-template-rows: auto minmax(0, 1fr) !important; }
  .workspace-sidebar { overflow-x: auto; padding: 7px; border-right: 0; border-bottom: 1px solid var(--shell-line); }
  .workspace-nav { display: flex; width: max-content; }
  .workspace-nav-group { display: flex; }
  .workspace-nav-group.active .workspace-subnav { display: flex; }
  .workspace-nav-button { width: auto; min-width: 92px; min-height: 38px; grid-template-columns: 20px auto; padding: 6px 8px; }
  .workspace-nav-copy small { display: none; }
  .workspace-subnav { margin: 0 3px; padding: 3px; border: 0; align-items: center; }
  .workspace-subnav-button { white-space: nowrap; }
  .workspace-main { padding: 8px; }
  .workspace-frame-host { height: calc(100vh - 124px); min-height: 560px; }
}
@media (max-width: 520px) {
  .workspace-main { padding: 0; }
  .workspace-frame-host { height: calc(100vh - 110px); min-height: 560px; border: 0; border-radius: 0; box-shadow: none; }
}
/* Keep the responsive grid after the desktop shell skin declarations. */
@media (max-width: 880px) {
  .workspace-body { grid-template-columns: minmax(0, 1fr) !important; grid-template-rows: auto minmax(0, 1fr) !important; }
  .workspace-sidebar { overflow-x: auto; padding: 7px; border-right: 0; border-bottom: 1px solid var(--shell-line); }
  .workspace-nav { display: flex; width: max-content; }
  .workspace-nav-group { display: flex; }
  .workspace-nav-group.active .workspace-subnav { display: flex; }
  .workspace-nav-button { width: auto; min-width: 92px; min-height: 38px; grid-template-columns: 20px auto; padding: 6px 8px; }
  .workspace-nav-copy small { display: none; }
  .workspace-subnav { margin: 0 3px; padding: 3px; border: 0; align-items: center; }
  .workspace-subnav-button { white-space: nowrap; }
  .workspace-main { padding: 8px; }
  .workspace-frame-host { height: calc(100vh - 124px); min-height: 560px; }
}
@media (max-width: 520px) {
  .workspace-main { padding: 0; }
  .workspace-frame-host { height: calc(100vh - 110px); min-height: 560px; border: 0; border-radius: 0; box-shadow: none; }
}
"""

SHELL_CSS += Path(__file__).with_name("assets").joinpath("styles", "workspace.css").read_text(encoding="utf-8")
SHELL_CSS += Path(__file__).with_name("assets").joinpath("styles", "notifications.css").read_text(encoding="utf-8")

_SHELL_JS_TEMPLATE = r"""
() => {
  const modules = __MODULES__;
  const routing = __ROUTING__;
  const resolveTarget = (module, view = "") => {
    const row = routing.aliases.find((item) => item.module === module && item.view === (view || ""));
    return row ? {module: row.target, view: row.target_view, tab: row.tab || ""} : {module, view: view || "", tab: ""};
  };
  const cacheLimit = __CACHE_LIMIT__;
  const marketStorageKey = "all-in-one-ui-market";
  const themeStorageKey = "all-in-one-ui-theme";

  const initialize = () => {
    const shell = document.getElementById("quant-workspace-shell");
    if (!shell || shell.dataset.initialized === "1") return false;
    shell.dataset.initialized = "1";

    const host = shell.querySelector("#workspace-frame-host");
    const status = shell.querySelector("#workspace-frame-status");
    const refreshButton = shell.querySelector("#workspace-refresh");
    const standaloneButton = shell.querySelector("#workspace-open-standalone");
    const sidebarToggle = shell.querySelector("#workspace-sidebar-toggle");
    const themeButton = shell.querySelector("#app-theme-toggle");
    const buttons = Array.from(shell.querySelectorAll("[data-workspace-module]"));
    const viewButtons = Array.from(shell.querySelectorAll("[data-workspace-view]"));
    const frames = new Map();
    const dirtyModules = new Set();
    let activeUrl = location.href;
    const recent = [];
    const known = new Map(modules.map((item) => [item.key, item]));
    const viewSelections = new Map();
    const initialUrl = new URL(window.location.href);
    const initial = resolveTarget(initialUrl.searchParams.get("module") || modules[0]?.key, initialUrl.searchParams.get("view"));
    const initialKey = initial.module;
    const initialView = initial.view;
    const validContext = (key, value) => routing.context_values?.[key] ? routing.context_values[key].includes(value) : /^[0-9]+$/.test(value || "");
    const targets = new Map();
    let routeSequence = 0;
    const targetKey = (module, view) => `${module}/${view}`;
    const targetState = (module, view) => targets.get(targetKey(module, view)) || {context: {}, tab: "", pipeline_version: "", nonce: `plain:${module}/${view}`};
    const remember = (module, view, data) => {
      const key = targetKey(module, view);
      const fields = routing.context_targets[key] || [];
      targets.set(key, {
        context: Object.fromEntries(Object.entries(data.context || {}).filter(([name,value]) => fields.includes(name) && validContext(name,value))),
        tab: routing.tabs.includes(data.tab) ? data.tab : "",
        pipeline_version: key === routing.pipeline_target && /^[0-9]+$/.test(String(data.pipeline_version || "")) ? String(data.pipeline_version) : "",
        nonce: `route:${++routeSequence}`,
      });
    };
    const readUrl = (url, destination) => remember(destination.module, destination.view || known.get(destination.module)?.views[0]?.key, {
      context: Object.fromEntries(Object.keys(routing.context_fields).map((key) => [key, url.searchParams.get(key)])),
      tab: destination.tab || url.searchParams.get("tab"), pipeline_version: url.searchParams.get("pipeline_version"),
    });
    readUrl(initialUrl, initial);
    if (initialKey && initialView) viewSelections.set(initialKey, initialView);
    let activeKey = "";
    let activeView = "";
    let currentTheme = "light";
    const configuredTheme = shell.dataset.themeDefault || "light";
    const resolveTheme = (theme) => theme === "system"
      ? (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : (theme === "dark" ? "dark" : "light");
    const applyShellTheme = (theme, persist = true) => {
      const selected = ["light", "dark", "system"].includes(theme) ? theme : "light";
      const resolved = resolveTheme(selected);
      currentTheme = resolved;
      document.documentElement.dataset.theme = resolved;
      document.documentElement.dataset.themePreference = selected;
      if (persist) localStorage.setItem(themeStorageKey, selected);
      frames.forEach((frame) => frame.contentWindow.postMessage({ type: "aiquant:theme", theme: resolved }, window.location.origin));
      const label = shell.querySelector("#app-theme-label");
      if (label) label.textContent = resolved === "dark" ? "深色" : "浅色";
    };

    const appMatch = window.location.pathname.match(/^(.*\/app)\/?$/);
    const appBase = appMatch ? `${appMatch[1]}/` : "/app/";
    const moduleUrl = (item, embedded = true) =>
      `${appBase}${item.slug}/${embedded ? "?embedded=1" : ""}`;
    const selectedView = (item) => {
      const views = item.views || [];
      const stored = viewSelections.get(item.key);
      if (stored && views.some((view) => view.key === stored)) return stored;
      return views[0]?.key || "";
    };
    const viewLabel = (item, viewKey) =>
      (item.views || []).find((view) => view.key === viewKey)?.label || "";
    const postView = (frame, item) => {
      const view = selectedView(item);
      const label = viewLabel(item, view);
      const target = targetState(item.key, view);
      if (!label) return;
      frame.contentWindow.postMessage(
        { type: "aiquant:select-view", module: item.key, view, label, tab: target.tab, context: target.context, pipeline_version: target.pipeline_version, target_nonce: target.nonce },
        window.location.origin,
      );
    };

    const setStatus = (text) => {
      status.textContent = text || "";
      status.hidden = !text;
    };
    const touch = (key) => {
      const index = recent.indexOf(key);
      if (index >= 0) recent.splice(index, 1);
      recent.push(key);
    };
    const trimCache = () => {
      while (frames.size > cacheLimit) {
        const removable = recent.find((key) => key !== activeKey);
        if (!removable) return;
        const frame = frames.get(removable);
        if (frame) frame.remove();
        frames.delete(removable);
        recent.splice(recent.indexOf(removable), 1);
      }
    };
    const frameFor = (item) => {
      let frame = frames.get(item.key);
      if (frame) return frame;
      frame = document.createElement("iframe");
      frame.className = "workspace-frame";
      frame.dataset.moduleKey = item.key;
      frame.title = item.title;
      frame.loading = "eager";
        frame.allowFullscreen = true;
      frame.src = moduleUrl(item);
      frame.addEventListener("load", () => {
        if (activeKey === item.key) {
          frame.contentWindow.postMessage({ type: "aiquant:theme", theme: currentTheme }, window.location.origin);
          postView(frame, item);
        }
      });
      host.appendChild(frame);
      frames.set(item.key, frame);
      return frame;
    };
    const select = (key, options = {}) => {
      const item = known.get(key) || modules[0];
      if (!item) return;
      if (activeKey !== item.key && dirtyModules.has(activeKey)) {
        if (!confirm("Markdown有未保存修改，是否放弃修改并切换模块？")) {
          if (options.history === false) history.replaceState({}, "", activeUrl);
          return;
        }
        dirtyModules.delete(activeKey);
        frames.get(activeKey)?.contentWindow.postMessage({type:"aiquant:preview-discard"}, location.origin);
      }
      if (activeKey && activeKey !== item.key) frames.get(activeKey)?.contentWindow.postMessage({type: "aiquant:deactivate"}, window.location.origin);
      activeKey = item.key;
      activeView = selectedView(item);
      viewSelections.set(item.key, activeView);
      buttons.forEach((button) => {
        const active = button.dataset.workspaceModule === item.key;
        button.classList.toggle("active", active);
        if (active) button.setAttribute("aria-current", "page");
        else button.removeAttribute("aria-current");
      });
      const activeButton = buttons.find((button) => button.dataset.workspaceModule === item.key);
      if (activeButton && window.innerWidth <= 880) {
        activeButton.scrollIntoView({ block: "nearest", inline: "center" });
      }
      shell.querySelectorAll(".workspace-nav-group").forEach((group) => {
        group.classList.toggle("active", group.dataset.workspaceGroup === item.key);
      });
      viewButtons.forEach((button) => {
        button.classList.toggle(
          "active",
          button.dataset.workspaceViewModule === item.key && button.dataset.workspaceView === activeView,
        );
      });
      frames.forEach((frame, frameKey) => frame.classList.toggle("active", frameKey === item.key));
      if (!frames.has(item.key)) setStatus(`正在加载${item.title}...`);
      const frame = frameFor(item);
      frame.classList.add("active");
      postView(frame, item);
      touch(item.key);
      trimCache();
      document.title = `${item.title} - AIQuant智投`;
      if (options.history !== false) {
        const url = new URL(window.location.href);
        url.searchParams.set("module", item.key);
        if (activeView) url.searchParams.set("view", activeView);
        else url.searchParams.delete("view");
        const target = targetState(item.key, activeView);
        if (target.tab) url.searchParams.set("tab", target.tab);
        else url.searchParams.delete("tab");
        if (target.pipeline_version) url.searchParams.set("pipeline_version", target.pipeline_version);
        else url.searchParams.delete("pipeline_version");
        Object.keys(routing.context_fields).forEach((name) => {
          if (validContext(name, target.context[name])) url.searchParams.set(name, target.context[name]);
          else url.searchParams.delete(name);
        });
        window.history.pushState({ module: item.key }, "", url);
      }
      activeUrl = location.href;
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => select(button.dataset.workspaceModule));
    });
    viewButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const moduleKey = button.dataset.workspaceViewModule;
        const viewKey = button.dataset.workspaceView;
        if (!moduleKey || !viewKey) return;
        viewSelections.set(moduleKey, viewKey);
        select(moduleKey);
        const frame = frames.get(moduleKey);
        const item = known.get(moduleKey);
        if (frame) {
          postView(frame, item);
        }
      });
    });
    refreshButton.addEventListener("click", () => {
      const frame = frames.get(activeKey);
      if (!frame) return;
      setStatus("正在刷新当前模块...");
      frame.contentWindow.location.reload();
    });
    standaloneButton.addEventListener("click", () => {
      const item = known.get(activeKey) || modules[0];
      if (!item) return;
      const view = selectedView(item), target = targetState(item.key, view);
      const url = new URL(moduleUrl(item, false), window.location.origin);
      url.searchParams.set("view", view);
      if (target.tab) url.searchParams.set("tab", target.tab);
      if (target.pipeline_version) url.searchParams.set("pipeline_version", target.pipeline_version);
      Object.entries(target.context).forEach(([key,value]) => url.searchParams.set(key, value));
      window.open(url.href, "_blank", "noopener,noreferrer");
    });
    const setSidebarCollapsed = (collapsed, persist = true) => {
      shell.classList.toggle("sidebar-collapsed", collapsed);
      if (sidebarToggle) {
        const label = collapsed ? "展开导航栏" : "收起导航栏";
        sidebarToggle.setAttribute("aria-label", label);
        sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
        sidebarToggle.title = label;
      }
      if (persist) localStorage.setItem("all-in-one-sidebar-collapsed", collapsed ? "1" : "0");
      frames.forEach((frame) => frame.contentWindow.postMessage({type: "aiquant:resize"}, window.location.origin));
    };
    sidebarToggle?.addEventListener("click", () => {
      setSidebarCollapsed(!shell.classList.contains("sidebar-collapsed"));
    });
    themeButton?.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyShellTheme(next);
    });
    shell.querySelectorAll("[data-workspace-market]").forEach((button) => {
      const market = button.dataset.workspaceMarket;
      button.classList.toggle("active", (localStorage.getItem(marketStorageKey) || "cn") === market);
      button.addEventListener("click", () => {
        localStorage.setItem(marketStorageKey, market);
        shell.querySelectorAll("[data-workspace-market]").forEach((item) => {
          item.classList.toggle("active", item.dataset.workspaceMarket === market);
        });
        const frame = frames.get(activeKey);
        if (frame) {
          setStatus("正在切换市场...");
          frame.contentWindow.location.reload();
        }
      });
    });
    const languageButton = shell.querySelector("#app-language-toggle");
    if (languageButton) {
      languageButton.addEventListener("click", () => {
        const market = localStorage.getItem(marketStorageKey) || "cn";
        shell.querySelectorAll("[data-workspace-market]").forEach((item) => {
          item.classList.toggle("active", item.dataset.workspaceMarket === market);
        });
        const frame = frames.get(activeKey);
        if (frame) {
          setStatus("正在切换界面语言...");
          frame.contentWindow.location.reload();
        }
      });
    }
    window.addEventListener("message", (event) => {
      if (event.origin !== window.location.origin) return;
      const sender = Array.from(frames.values()).find((item) => item.contentWindow === event.source);
      if (!sender) return;
      if (event.data?.type === "aiquant:preview-dirty-state") {
        if (event.data.dirty) dirtyModules.add(sender.dataset.moduleKey);
        else dirtyModules.delete(sender.dataset.moduleKey);
        return;
      }
      if (event.data?.type === "aiquant:context-edited" && sender.dataset.moduleKey === activeKey) {
        const {view, name, value} = event.data, key = targetKey(activeKey, activeView);
        if (view !== activeView || !(routing.context_targets[key] || []).includes(name) || (value && !validContext(name,value))) return;
        const target = targetState(activeKey, activeView);
        if (value) target.context[name] = value; else delete target.context[name];
        targets.set(key, target);
        const url = new URL(location.href);
        if (value) url.searchParams.set(name, value); else url.searchParams.delete(name);
        history.replaceState({}, "", url);
        return;
      }
      if (event.data?.type === "aiquant:view-selected" && sender.dataset.moduleKey === activeKey) {
        const item = known.get(activeKey), view = event.data.view;
        if (item.views.some((row) => row.key === view)) {
          viewSelections.set(activeKey, view);
          select(activeKey);
        }
        return;
      }
      if (event.data?.type === "aiquant:ready") {
        const frame = Array.from(frames.values()).find((item) => item.contentWindow === event.source);
        const item = frame ? known.get(frame.dataset.moduleKey) : null;
        if (frame && item) {
          if (activeKey === item.key) setStatus("");
          frame.contentWindow.postMessage({ type: "aiquant:theme", theme: currentTheme }, window.location.origin);
          if (activeKey === item.key) postView(frame, item);
        }
        return;
      }
      if (event.data?.type === "aiquant:navigate") {
        if (sender.dataset.moduleKey !== activeKey) return;
        const destination = resolveTarget(event.data.module, event.data.view);
        if (!known.has(destination.module)) return;
        const requested = String(destination.view || "");
        if (known.get(destination.module).views.some((item) => item.key === requested)) viewSelections.set(destination.module, requested);
        remember(destination.module, selectedView(known.get(destination.module)), {...event.data, tab: destination.tab || event.data.tab});
        select(destination.module);
        const frame = frames.get(destination.module);
        if (frame) postView(frame, known.get(destination.module));
      }
    });
    window.addEventListener("popstate", () => {
      const url = new URL(window.location.href);
      const destination = resolveTarget(url.searchParams.get("module") || modules[0]?.key, url.searchParams.get("view"));
      const key = destination.module;
      const view = destination.view;
      readUrl(url, destination);
      if (key && view) viewSelections.set(key, view);
      select(key, { history: false });
      const frame = frames.get(key);
      const item = known.get(key);
      if (frame && item) postView(frame, item);
    });
    window.addEventListener("aiquant:notification-open", event => {
      const data = event.detail || {}, destination = resolveTarget(data.module, data.view);
      const item = known.get(destination.module);
      if (!item || !item.views.some(view => view.key === destination.view)) return;
      viewSelections.set(item.key, destination.view);
      remember(item.key, destination.view, {context: {task_id: String(data.task_id || "")}});
      select(item.key);
    });

    const savedSidebar = localStorage.getItem("all-in-one-sidebar-collapsed");
    window.addEventListener("beforeunload", (event) => {if(dirtyModules.size){event.preventDefault();event.returnValue="";}});
    setSidebarCollapsed(savedSidebar === "1" || (savedSidebar === null && window.innerWidth <= 880), false);
    applyShellTheme(localStorage.getItem(themeStorageKey) || configuredTheme, false);
    select(initialKey, { history: false });
    return true;
  };

  if (!initialize()) {
    const observer = new MutationObserver(() => {
      if (initialize()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
}
"""


def _module_payload() -> list[dict[str, Any]]:
    return [
        {
            "key": module.key,
            "title": module.title,
            "slug": module.slug,
            "description": module.description,
            "views": [{"key": view_key, "label": label} for view_key, label in module.views],
        }
        for module in MODULES
    ]


SHELL_JS = (
    _SHELL_JS_TEMPLATE.replace(
        "__MODULES__",
        json.dumps(_module_payload(), ensure_ascii=False),
    )
    .replace("__CACHE_LIMIT__", str(SHELL_CACHE_LIMIT))
    .replace("__ROUTING__", json.dumps(navigation_config(), ensure_ascii=False))
)


def _icon_button(button_id: str, title: str, path: str) -> str:
    return (
        f"<button id='{button_id}' class='workspace-icon-button' type='button' title='{escape(title)}' "
        f"aria-label='{escape(title)}'><svg viewBox='0 0 24 24' aria-hidden='true'><path d='{path}' "
        "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
        "stroke-linejoin='round'/></svg></button>"
    )


def _language_button() -> str:
    return (
        "<button id='app-language-toggle' class='workspace-icon-button workspace-language-button' "
        "type='button' title='切换中英文界面 / Toggle UI language' aria-label='切换中英文界面'>"
        "<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M3 5h9M7.5 3.5v1.5c0 4.5-2 8.5-4.5 10.5M5 9"
        "c1.5 3 4 5.5 7 6.5M13 20.5l4-11 4 11M14.8 17h4.4' fill='none' stroke='currentColor' "
        "stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>"
        "<span id='app-language-label'>中 / EN</span></button>"
    )


def _theme_button() -> str:
    return (
        "<button id='app-theme-toggle' class='workspace-icon-button workspace-theme-button' type='button' "
        "title='切换深色主题' aria-label='切换深色主题'>"
        "<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M20.5 15.3A8.5 8.5 0 0 1 8.7 3.5 8.5 8.5 0 1 0 20.5 15.3Z' "
        "fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>"
        "<span id='app-theme-label'>浅色</span></button>"
    )


def shell_html(theme_mode: str = "light") -> str:
    """Return the persistent shell markup with a flat global module rail."""
    navigation_items: list[str] = []
    for module in MODULES:
        button = (
            f"<button class='workspace-nav-button has-tooltip' type='button' data-workspace-module='{escape(module.key)}' "
            f"title='{escape(module.description)}' data-tooltip='{escape(module.description)}'>"
            f"<span class='workspace-nav-icon' data-icon='{escape(module.key)}' aria-hidden='true'>{module_icon(module.key)}</span>"
            f"<span class='workspace-nav-copy'><strong>{escape(module.title)}</strong>"
            f"<small>{escape(module.description)}</small></span></button>"
        )
        subnavigation = "".join(
            f"<button class='workspace-subnav-button has-tooltip' type='button' title='打开{escape(label)}页面' "
            f"data-tooltip='打开{escape(label)}页面；查看该功能的详细结果' "
            f"data-workspace-view-module='{escape(module.key)}' data-workspace-view='{escape(view)}'>"
            f"{escape(label)}</button>"
            for view, label in module.views
        )
        navigation_items.append(
            f"<div class='workspace-nav-group' data-workspace-group='{escape(module.key)}'>"
            f"{button}<div class='workspace-subnav'>{subnavigation}</div></div>"
        )
    navigation = "".join(navigation_items)
    refresh = _icon_button(
        "workspace-refresh",
        "刷新当前模块",
        "M20 11a8 8 0 0 0-13.7-4.7L4 8.5M4 4v4.5h4.5M4 13a8 8 0 0 0 13.7 4.7l2.3-2.2M20 20v-4.5h-4.5",
    )
    standalone = _icon_button(
        "workspace-open-standalone",
        "在新窗口打开当前模块",
        "M14 3h7v7M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5",
    )
    language = _language_button()
    sidebar_toggle = _icon_button("workspace-sidebar-toggle", "收起导航栏", "M14 6l-6 6 6 6")
    sidebar_toggle = sidebar_toggle.replace(
        "type='button'", "type='button' aria-controls='workspace-sidebar' aria-expanded='true'"
    )
    return (
        f"<div id='quant-workspace-shell' class='workspace-shell' data-theme-default='{escape(theme_mode)}'>"
        "<header class='workspace-topbar'><div class='workspace-brand'>"
        "<img src='/static/logo.png' alt='AIQuant智投 Logo'/><div class='workspace-brand-copy'>"
        "<strong>AIQuant智投</strong><span>一体化量化研究与交易工作台</span></div></div>"
        f"<div class='workspace-actions'><div class='workspace-external-links'>{external_links_html()}</div>"
        f"<button id='workspace-notification-toggle' type='button' data-config-url='{escape(get_settings().api_prefix)}/notifications/config' data-retry-seconds='{notification_config()['backoff_seconds']}' data-offline='{escape(notification_config()['ui']['offline'])}' aria-label='提醒中心'>"
        "<svg viewBox='0 0 24 24' width='19' height='19' fill='none' stroke='currentColor' stroke-width='1.8'><path d='M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4'/></svg><span></span></button>"
        "<div class='workspace-market' role='group' aria-label='市场切换'>"
        "<button id='app-market-cn' type='button' data-workspace-market='cn'>A股</button>"
        "<button id='app-market-us' type='button' data-workspace-market='us'>美股</button></div>"
        f"{language}{_theme_button()}{refresh}{standalone}</div></header>"
        "<div class='workspace-body'><aside id='workspace-sidebar' class='workspace-sidebar'>"
        f"<div class='workspace-sidebar-tools'>{sidebar_toggle}</div>"
        f"<nav class='workspace-nav' aria-label='主功能导航'>{navigation}</nav></aside>"
        "<main class='workspace-main'><div id='workspace-frame-status' class='workspace-frame-status' hidden></div>"
        "<div id='workspace-frame-host' class='workspace-frame-host'></div></main></div></div>"
    )


def shell_runtime_js(theme_mode: str = "light") -> str:
    notices = Path(__file__).with_name("assets").joinpath("notifications.js").read_text(encoding="utf-8")
    return f"() => {{ ({theme_runtime_js(theme_mode)})(); ({SHELL_JS})(); ({notices})(); }}"


SHELL_RUNTIME_JS = shell_runtime_js()


def shell_gradio_mount_options(theme_mode: str = "light") -> dict[str, Any]:
    """Return Gradio mount options dedicated to the workspace shell."""
    options = dict(gradio_mount_options(theme_mode))
    if "css" in options:
        options["css"] = SHELL_CSS
    if "js" in options:
        options["js"] = shell_runtime_js(theme_mode)
    return options


def build_gradio_shell(theme_mode: str = "light") -> gr.Blocks:
    """Build the small persistent shell without constructing business modules."""
    blocks_options: dict[str, Any] = {"title": "AIQuant智投", "fill_width": True}
    if supports_parameter(gr.Blocks, "theme"):
        blocks_options.update(theme=theme(), css=SHELL_CSS, js=shell_runtime_js(theme_mode))

    with gr.Blocks(**blocks_options) as demo:
        gr.HTML(
            shell_html(theme_mode),
            elem_id="workspace-shell-root",
            js_on_load=f"({shell_runtime_js(theme_mode)})();",
        )
    return demo
