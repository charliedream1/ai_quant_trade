# -*- coding: utf-8 -*-
"""
Auto-generate docs/_projects/ wrapper pages, mkdocs.yml nav, and the
project-grid section of docs/index.md from a single filesystem walk.

Single source of truth: the egs/ai_notes/egs_skill markdown files.
When you add / remove / rename a README, run this script (or rely on CI
which runs it as a pre-build step) and everything stays in sync.

Adding a new egs project:
    1. Create the README under the right egs_<category>/.../README.md path
       (the location determines which category / subcategory it belongs to).
    2. Optionally add a LABEL_OVERRIDES entry if the auto-derived label
       (last path component) is not what you want on the site.
    3. If the project lives under a root we haven't listed in DISCOVERY_RULES,
       add one rule (rare). Run `python zz_scripts/gen_project_wrappers.py`
       and commit the regenerated mkdocs.yml / docs/index.md / wrappers.

Outputs:
    - docs/_projects/<group>/<slug>.md           (wrapper pages)
    - mkdocs.yml                                 (nav: section between markers)
    - docs/index.md                              (project grid between markers)

Marker convention:
    - mkdocs.yml:    `# >>> AUTO-NAV-START` ... `# <<< AUTO-NAV-END`
    - docs/index.md: `<!-- >>> AUTO-INDEX-START` ... `<!-- <<< AUTO-INDEX-END`
    （注意：标记本身不包含 ` -->` 闭合符，所以注释里可以附带说明文本，匹配更稳健）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]  # ai_quant_trade
DOCS_PROJECTS_DIR = REPO_ROOT / "docs" / "_projects"
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
INDEX_MD = REPO_ROOT / "docs" / "index.md"

NAV_START = "# >>> AUTO-NAV-START"
NAV_END = "# <<< AUTO-NAV-END"
INDEX_START = "<!-- >>> AUTO-INDEX-START"
INDEX_END = "<!-- <<< AUTO-INDEX-END"


# ---------------------------------------------------------------------------
# Discovery rules
# ---------------------------------------------------------------------------
# Each rule: (root, outer_group, category, subcategory, include_pattern)
# - outer_group: top-level nav group ("项目集", "教程 FAQ", "学习笔记")
# - category:   the sub-category inside outer_group ("交易策略", "数据源")
# - subcategory: optional sub-sub-category for data sources ("股票", "基金")
# - include_pattern: glob string OR list of glob strings relative to root
# ---------------------------------------------------------------------------
DISCOVERY_RULES: list[tuple[str, str, str, str | None, str | list[str]]] = [
    # 项目集 → 交易策略
    ("egs_trade/vanilla",          "项目集", "交易策略", None, "*/README.md"),
    ("egs_trade/vanilla/double_ma", "项目集", "交易策略", None, "文档教程/README.md"),
    ("egs_trade/ms_qlib",          "项目集", "交易策略", None, "README.md"),
    # egs_trade/rl 下 README 分布在 1 段和 2 段目录里，分别匹配
    ("egs_trade/rl/a001_proto_sb3", "项目集", "交易策略", None, "README.md"),
    ("egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018",
                                       "项目集", "交易策略", None, "README.md"),
    ("egs_trade/paper_trade",      "项目集", "交易策略", None, "*/README.md"),

    # 项目集 → 数据源（带 subcategory）
    ("egs_data/股票",                "项目集", "数据源", "股票",     "*/README.md"),
    # wind 下还嵌套 basic_data 等子目录
    ("egs_data/股票/wind",           "项目集", "数据源", "股票",     "*/README.md"),
    ("egs_data/基金",                "项目集", "数据源", "基金",     "*/README.md"),
    ("egs_data/期货",                "项目集", "数据源", "期货",     "*/README.md"),
    ("egs_data/电子币",              "项目集", "数据源", "加密货币", "*/README.md"),
    ("egs_data/宏观经济",            "项目集", "数据源", "宏观经济", "*/README.md"),
    ("egs_data/新闻",                "项目集", "数据源", "新闻",     "*/README.md"),

    # 项目集 → 因子挖掘
    ("egs_alpha/alpha_libs",         "项目集", "因子挖掘", None, "*/README.md"),
    ("egs_alpha/auto_alpha",         "项目集", "因子挖掘", None, ["README.md", "tsfresh/README.md"]),

    # 项目集 → 大模型与 Skill
    ("egs_llm/a01_train/a01_unsloth_stock_forcaster", "项目集", "大模型与 Skill", None, "README.md"),
    ("egs_llm/a01_train/a01_unsloth_stock_forcaster/a01_download_mdl", "项目集", "大模型与 Skill", None, "README.md"),
    ("egs_llm/a01_train/a01_unsloth_stock_forcaster/a04_train", "项目集", "大模型与 Skill", None, "README.md"),
    ("egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet", "项目集", "大模型与 Skill", None, "README.md"),
    ("egs_skill/broker-research-analyst", "项目集", "大模型与 Skill", None, "README.md"),

    # 项目集 → 金融 NLP
    ("egs_fin_nlp",                  "项目集", "金融 NLP", None, "*/*/README.md"),

    # 项目集 → 在线平台
    ("egs_online_platform",          "项目集", "在线平台", None, "*/说明.md"),

    # 项目集 → 辅助工具
    # 看盘神器下嵌套 v1/v2 子目录
    ("egs_aide",                     "项目集", "辅助工具", None, "*/README.md"),
    ("egs_aide/看盘神器",            "项目集", "辅助工具", None, "*/README.md"),

    # 教程 FAQ
    ("egs_llm/a01_train/a01_unsloth_stock_forcaster/a00_FAQ", "教程 FAQ", "教程 FAQ", None, "01_FAQ.md"),
    ("egs_skill",                    "教程 FAQ", "教程 FAQ", None,
        ["SKILL.md", "PROPOSAL.md", "SOURCE.md", "BACKTEST_REPORT.md",
         "E2E_TEST_REPORT.md", "PDF_PARSER_RESEARCH.md", "PDF_IMAGE_RESEARCH.md"]),
    ("egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018", "教程 FAQ", "教程 FAQ", None, "RESULT.md"),

    # 学习笔记
    ("ai_notes/03_论文",             "学习笔记", "学习笔记", None, ["README.md", "01_papers_with_code.md"]),
    ("ai_notes/03_论文/01_大模型/01_通用金融", "学习笔记", "学习笔记", None, "*.md"),
]

# Display-label overrides: (source_path_rel_to_repo_root, friendly_label).
# Keys NOT in here fall back to the auto-derived label (parent dir's friendly
# name, falling back to the file stem).
LABEL_OVERRIDES: dict[str, str] = {
    "egs_trade/vanilla/double_ma/README.md": "双均线策略",
    "egs_trade/vanilla/double_ma/文档教程/README.md": "文档教程",
    "egs_trade/vanilla/momentum_rotation/README.md": "动量轮动",
    "egs_trade/vanilla/portfolio_optimization/README.md": "组合优化",
    "egs_trade/rl/a001_proto_sb3/README.md": "PPO 强化学习",
    "egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018/README.md": "finRL NeurIPS 复现",
    "egs_trade/paper_trade/wind/README.md": "Wind 实盘",
    "egs_llm/a01_train/a01_unsloth_stock_forcaster/README.md": "Unsloth 训练",
    "egs_llm/a01_train/a01_unsloth_stock_forcaster/a01_download_mdl/README.md": "模型下载",
    "egs_llm/a01_train/a01_unsloth_stock_forcaster/a04_train/README.md": "模型训练",
    "egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet/README.md": "热点报告",
    "egs_skill/broker-research-analyst/README.md": "券商研报 Skill",
    "egs_llm/a01_train/a01_unsloth_stock_forcaster/a00_FAQ/01_FAQ.md": "Unsloth FAQ",
    "egs_skill/broker-research-analyst/SKILL.md": "Skill 文档",
    "egs_skill/PROPOSAL.md": "Skill 提案",
    "egs_skill/SOURCE.md": "Skill 资料",
    "egs_skill/BACKTEST_REPORT.md": "回测报告",
    "egs_skill/E2E_TEST_REPORT.md": "E2E 测试报告",
    "egs_skill/PDF_PARSER_RESEARCH.md": "PDF 解析研究",
    "egs_skill/PDF_IMAGE_RESEARCH.md": "PDF 图片研究",
    "egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018/RESULT.md": "finRL 复现结果",
    "ai_notes/03_论文/README.md": "论文笔记",
    "ai_notes/03_论文/01_papers_with_code.md": "论文导航",
    "ai_notes/03_论文/01_大模型/01_通用金融/01_GPT金融分析.md": "GPT 金融分析",
}

# Manual entries for one-offs that don't fit any discovery rule.
# (label, source_repo_rel, slug, subdir)
MANUAL: list[tuple[str, str, str, str]] = []


# ---------------------------------------------------------------------------
# Wrapper template
# ---------------------------------------------------------------------------
WRAPPER_TEMPLATE = """# {label}

!!! note "本页内容来源"
    以下内容来自项目仓库原始文档，编辑请直接修改源文件：
    `{source_path}`

{{{{% include "{include_path}" %}}}}
"""


# ---------------------------------------------------------------------------
# Core data class
# ---------------------------------------------------------------------------
class Project:
    __slots__ = ("label", "source_rel", "slug", "subdir")

    def __init__(self, label: str, source_rel: str, slug: str, subdir: str) -> None:
        self.label = label
        self.source_rel = source_rel
        self.slug = slug
        self.subdir = subdir

    @property
    def abs_source(self) -> Path:
        return (REPO_ROOT / self.source_rel).resolve()

    @property
    def exists(self) -> bool:
        return self.abs_source.is_file()


def _friendly_fallback(source_rel: str) -> str:
    """Auto-derive a label from the path when LABEL_OVERRIDES has no entry."""
    p = Path(source_rel)
    # Prefer the parent dir name over the file stem
    if p.stem.lower() in {"readme", "01_faq", "说明", "result", "skill",
                           "proposal", "source", "backtest_report",
                           "e2e_test_report", "pdf_parser_research",
                           "pdf_image_research"}:
        return p.parent.name or p.stem
    return p.stem


def _slug_for(source_rel: str) -> str:
    """Stable wrapper slug from the source path.

    Includes both the parent dir name AND a stable form of the filename so
    siblings like `egs_skill/SKILL.md` and `egs_skill/PROPOSAL.md` get
    distinct slugs (the parent alone would collide).
    """
    p = Path(source_rel)
    stem = p.parent.name or p.stem
    parent = p.parent.as_posix().replace("/", "_").replace(".", "_")
    parent = re.sub(r"_+", "_", parent).strip("_")
    # If the filename carries information beyond "README"/"说明" etc.,
    # append a sanitized version so siblings don't collide.
    if p.stem.lower() not in {"readme", "01_faq", "说明", "result"}:
        file_part = re.sub(r"[^0-9A-Za-z_\-]+", "_", p.stem).strip("_")
        return f"{stem}__{parent}__{file_part}"
    return f"{stem}__{parent}" if parent else stem


def _subdir_for(outer_group: str, category: str | None, subcategory: str | None,
                slug: str) -> str:
    """The wrapper output sub-directory (also used as nav key under 项目集)."""
    if outer_group == "项目集":
        # Categories like 交易策略 / 数据源 / 因子挖掘 ...
        return category or outer_group
    return outer_group  # 教程 FAQ, 学习笔记, etc.


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def _expand_glob(root: Path, pattern: str) -> list[Path]:
    """Glob one pattern relative to root. Return only files.

    Excludes pytest cache directories (.pytest_cache/) which often contain
    auto-generated README.md files that should NOT be exposed as projects.
    """
    return sorted(
        p for p in root.glob(pattern)
        if p.is_file() and ".pytest_cache" not in p.parts
    )


def discover_projects() -> list[Project]:
    """Walk all DISCOVERY_RULES + MANUAL, return deduplicated project list."""
    projects: list[Project] = []

    for root_rel, outer_group, category, subcategory, include in DISCOVERY_RULES:
        root = REPO_ROOT / root_rel
        if not root.is_dir():
            continue
        patterns = include if isinstance(include, list) else [include]
        matched: set[Path] = set()
        for pat in patterns:
            matched.update(_expand_glob(root, pat))
        for abs_path in sorted(matched):
            source_rel = abs_path.relative_to(REPO_ROOT).as_posix()
            label = LABEL_OVERRIDES.get(source_rel, _friendly_fallback(source_rel))
            subdir = _subdir_for(outer_group, category, subcategory, source_rel)
            slug = _slug_for(source_rel)
            projects.append(Project(label, source_rel, slug, subdir))

    # Manual additions (always win on collision)
    for label, source_rel, slug, subdir in MANUAL:
        # Replace any auto-discovered project with same source.
        projects = [p for p in projects if p.source_rel != source_rel]
        projects.append(Project(label, source_rel, slug, subdir))

    # Dedup by (source_rel) preserving first occurrence.
    seen: set[str] = set()
    unique: list[Project] = []
    for p in projects:
        if p.source_rel in seen:
            continue
        seen.add(p.source_rel)
        unique.append(p)
    return unique


# ---------------------------------------------------------------------------
# Wrapper-page generation
# ---------------------------------------------------------------------------
def write_wrappers(projects: list[Project]) -> tuple[list[str], list[str]]:
    """Return (written_paths, missing_sources)."""
    written: list[str] = []
    missing: list[str] = []
    DOCS_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    for proj in projects:
        if not proj.exists:
            missing.append(f"{proj.slug}: source not found: {proj.abs_source}")
            continue
        wrapper_path = DOCS_PROJECTS_DIR / proj.subdir / f"{proj.slug}.md"
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        # depth-3 from wrapper back to repo root (docs/_projects/<cat>/<slug>.md
        # → up 3 levels).
        include_path = f"../../../{proj.source_rel}"
        wrapper_path.write_text(
            WRAPPER_TEMPLATE.format(
                label=proj.label,
                source_path=proj.source_rel,
                include_path=include_path,
            ),
            encoding="utf-8",
        )
        written.append(str(wrapper_path.relative_to(REPO_ROOT)))
    return written, missing


def cleanup_stale_wrappers(projects: list[Project]) -> list[str]:
    """Remove wrapper files under DOCS_PROJECTS_DIR that are no longer
    referenced by the current project set. Also removes empty subdirs.

    Returns the list of removed paths (relative to repo root).
    """
    expected: set[Path] = set()
    for p in projects:
        expected.add((DOCS_PROJECTS_DIR / p.subdir / f"{p.slug}.md").resolve())

    removed: list[str] = []
    if not DOCS_PROJECTS_DIR.is_dir():
        return removed
    for path in DOCS_PROJECTS_DIR.rglob("*.md"):
        if path.resolve() not in expected:
            rel = path.relative_to(REPO_ROOT).as_posix()
            path.unlink()
            removed.append(rel)
    # Remove now-empty subdirectories.
    for sub in sorted(DOCS_PROJECTS_DIR.rglob("*"), reverse=True):
        if sub.is_dir() and not any(sub.iterdir()):
            sub.rmdir()
    return removed


# ---------------------------------------------------------------------------
# mkdocs.yml nav generation
# ---------------------------------------------------------------------------
def _yaml_escape_label(label: str) -> str:
    """Wrap label in quotes if it has special chars."""
    if re.search(r"[:\[\]/#&*!|>'\"%@`{}]", label):
        escaped = label.replace('"', '\\"')
        return f'"{escaped}"'
    return label


def _format_nav_label(label: str) -> str:
    return _yaml_escape_label(label)


def render_nav(projects: list[Project]) -> str:
    """Render the nav: block as YAML between markers."""
    # Group: outer_group → category → subcategory → [entries]
    tree: dict[str, dict[str, dict[str, list[Project]]]] = {}
    for p in projects:
        # Determine outer group / category / subcategory by reverse lookup.
        outer = _classify_outer(p)
        cat = _classify_category(p)
        sub = _classify_subcategory(p)
        tree.setdefault(outer, {}).setdefault(cat, {}).setdefault(sub, []).append(p)

    lines: list[str] = ["- 首页: index.md"]

    # Fixed ordering of outer groups.
    outer_order = ["项目集", "社区", "学习笔记", "教程 FAQ", "进阶", "部署运维"]
    outer_keys = [g for g in outer_order if g in tree]
    outer_keys += [g for g in tree if g not in outer_order]

    for outer in outer_keys:
        cat_map = tree[outer]
        # 项目集 has sub-categories; others do not.
        if outer == "项目集":
            lines.append(f"- {_format_nav_label(outer)}:")
            cat_order = ["交易策略", "数据源", "因子挖掘", "大模型与 Skill",
                         "金融 NLP", "在线平台", "辅助工具"]
            cat_keys = [c for c in cat_order if c in cat_map]
            cat_keys += [c for c in cat_map if c not in cat_order]
            for cat in cat_keys:
                sub_map = cat_map[cat]
                if cat == "数据源":
                    lines.append(f"    - {_format_nav_label(cat)}:")
                    sub_order = ["股票", "基金", "期货", "加密货币", "宏观经济", "新闻"]
                    sub_keys = [s for s in sub_order if s in sub_map]
                    sub_keys += [s for s in sub_map if s not in sub_order]
                    for sub in sub_keys:
                        entries = sorted(sub_map[sub], key=lambda p: p.label)
                        if len(entries) == 1:
                            lines.append(
                                f"        - {_format_nav_label(entries[0].label)}: "
                                f"_projects/{entries[0].subdir}/{entries[0].slug}.md"
                            )
                        else:
                            lines.append(f"        - {_format_nav_label(sub)}:")
                            for p in entries:
                                lines.append(
                                    f"            - {_format_nav_label(p.label)}: "
                                    f"_projects/{p.subdir}/{p.slug}.md"
                                )
                else:
                    entries = sorted(
                        [pp for subs in sub_map.values() for pp in subs],
                        key=lambda p: p.label,
                    )
                    if len(entries) == 1:
                        lines.append(
                            f"    - {_format_nav_label(cat)}: "
                            f"_projects/{entries[0].subdir}/{entries[0].slug}.md"
                        )
                    else:
                        lines.append(f"    - {_format_nav_label(cat)}:")
                        for p in entries:
                            lines.append(
                                f"        - {_format_nav_label(p.label)}: "
                                f"_projects/{p.subdir}/{p.slug}.md"
                            )
        else:
            # Flat single-level group: 社区 / 学习笔记 / 教程 FAQ / 进阶 / 部署运维
            entries = sorted(
                [pp for subs in cat_map.get(None, {}).values() for pp in subs]
                + [pp for cat in cat_map.values() for subs in cat.values() for pp in subs],
                key=lambda p: p.label,
            )
            if entries:
                lines.append(f"- {_format_nav_label(outer)}:")
                for p in entries:
                    lines.append(
                        f"    - {_format_nav_label(p.label)}: "
                        f"_projects/{p.subdir}/{p.slug}.md"
                    )

    return "\n".join(lines) + "\n"


def _classify_outer(p: Project) -> str:
    for root_rel, outer, _cat, _sub, _inc in DISCOVERY_RULES:
        root = REPO_ROOT / root_rel
        try:
            p.abs_source.relative_to(root)
            return outer
        except ValueError:
            continue
    return "项目集"


def _classify_category(p: Project) -> str:
    for root_rel, _outer, cat, _sub, _inc in DISCOVERY_RULES:
        root = REPO_ROOT / root_rel
        try:
            p.abs_source.relative_to(root)
            return cat
        except ValueError:
            continue
    return "其它"


def _classify_subcategory(p: Project) -> str | None:
    for root_rel, _outer, _cat, sub, _inc in DISCOVERY_RULES:
        root = REPO_ROOT / root_rel
        try:
            p.abs_source.relative_to(root)
            return sub
        except ValueError:
            continue
    return None


def update_mkdocs_nav(nav_text: str) -> None:
    """Replace content between NAV_START / NAV_END markers in mkdocs.yml."""
    original = MKDOCS_YML.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"({re.escape(NAV_START)})(.*?)({re.escape(NAV_END)})",
        re.DOTALL,
    )
    if not pattern.search(original):
        print(
            f"[gen_project_wrappers] ERROR: markers {NAV_START} / {NAV_END} "
            f"not found in mkdocs.yml",
            file=sys.stderr,
        )
        raise SystemExit(2)
    new_content = pattern.sub(
        lambda m: f"{NAV_START}\n{nav_text.rstrip()}\n  {NAV_END}",
        original,
    )
    _atomic_write(MKDOCS_YML, new_content)


# ---------------------------------------------------------------------------
# docs/index.md grid section (auto-maintained)
# 双语卡片区：英文版 + 中文版。两个 div 由同一组 Project 渲染，分类标题
# 用 CATEGORY_LABELS 映射，wrapper 链接保持 project.label（指向中文 wrapper）。
# ---------------------------------------------------------------------------

# 分类标题双语映射（zh -> en）。未列入则英文版回退到中文原文。
CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "交易策略":   {"zh": "交易策略",   "en": "Trading Strategies"},
    "数据源":     {"zh": "数据源",     "en": "Data Sources"},
    "因子挖掘":   {"zh": "因子挖掘",   "en": "Alpha Mining"},
    "大模型与 Skill": {"zh": "大模型与 Skill", "en": "LLM & Skills"},
    "金融 NLP":   {"zh": "金融 NLP",   "en": "Financial NLP"},
    "在线平台":   {"zh": "在线平台",   "en": "Online Platforms"},
    "辅助工具":   {"zh": "辅助工具",   "en": "Utilities"},
}
# 数据源子分类双语映射
SUBCATEGORY_LABELS: dict[str, dict[str, str]] = {
    "股票":     {"zh": "股票",     "en": "Stocks"},
    "基金":     {"zh": "基金",     "en": "Funds"},
    "期货":     {"zh": "期货",     "en": "Futures"},
    "加密货币": {"zh": "加密货币", "en": "Crypto"},
    "宏观经济": {"zh": "宏观经济", "en": "Macro"},
    "新闻":     {"zh": "新闻",     "en": "News"},
}
ICON_MAP: dict[str, str] = {
    "交易策略":       "material-chart-line",
    "数据源":         "material-database",
    "因子挖掘":       "material-flask",
    "大模型与 Skill": "material-robot",
    "金融 NLP":       "material-message-text",
    "在线平台":       "material-cloud",
    "辅助工具":       "material-tools",
}


def _label(cat: str, lang: str) -> str:
    """Return the display label for a category in the given language."""
    return CATEGORY_LABELS.get(cat, {}).get(lang, cat)


def _sublabel(sub: str, lang: str) -> str:
    return SUBCATEGORY_LABELS.get(sub, {}).get(lang, sub)


def _render_cards_block(cat_map: dict[str, list[Project]], lang: str) -> str:
    """Render all category card blocks for a single language."""
    cat_order = ["交易策略", "数据源", "因子挖掘", "大模型与 Skill",
                 "金融 NLP", "在线平台", "辅助工具"]
    keys = [c for c in cat_order if c in cat_map]
    keys += [c for c in cat_map if c not in cat_order]

    blocks: list[str] = []
    for cat in keys:
        ps = sorted(cat_map[cat], key=lambda p: p.label)
        icon = ICON_MAP.get(cat, "material-folder")
        cat_disp = _label(cat, lang)

        if cat == "数据源":
            # Group by subcategory for compact ·-separated lines.
            sub_map: dict[str | None, list[Project]] = {}
            for p in ps:
                sub_map.setdefault(_classify_subcategory(p), []).append(p)
            sub_order = ["股票", "基金", "期货", "加密货币", "宏观经济", "新闻"]
            sub_keys = [s for s in sub_order if s in sub_map]
            sub_keys += [s for s in sub_map if s not in sub_order and s is not None]
            sub_keys += [s for s in sub_map if s is None]

            if lang == "zh":
                count_str = f"（{len(ps)} 个数据源）"
            else:
                noun = "source" if len(ps) == 1 else "sources"
                count_str = f" ({len(ps)} {noun})"
            lines: list[str] = []
            for sub in sub_keys:
                if sub is None:
                    continue
                ps_sub = sorted(sub_map[sub], key=lambda p: p.label)
                rendered = " · ".join(
                    f"[{p.label}](_projects/{p.subdir}/{p.slug}.md)" for p in ps_sub
                )
                # 数据源展示不写子标题，直接按子分类分行
                if lang == "zh" and sub not in SUBCATEGORY_LABELS:
                    pass
                else:
                    pass
                lines.append(f"- {rendered}")
            blocks.append(
                f"-   :{icon}: __{cat_disp}{count_str}__\n\n"
                f"    ---\n\n"
                + "\n".join(lines)
                + "\n\n"
            )
        else:
            bullets = "\n".join(
                f"    - [{p.label}](_projects/{p.subdir}/{p.slug}.md)"
                for p in ps
            )
            if lang == "zh":
                count_str = f"（{len(ps)} 个项目）"
            else:
                noun = "project" if len(ps) == 1 else "projects"
                count_str = f" ({len(ps)} {noun})"
            blocks.append(
                f"-   :{icon}: __{cat_disp}{count_str}__\n\n"
                f"    ---\n\n{bullets}\n\n"
            )
    return "".join(blocks)


def render_index_cards(projects: list[Project]) -> str:
    """Render the bilingual (en + zh) 项目集 section of docs/index.md."""
    cat_map: dict[str, list[Project]] = {}
    for p in projects:
        cat = _classify_category(p)
        if _classify_outer(p) != "项目集":
            continue
        cat_map.setdefault(cat, []).append(p)

    en_blocks = _render_cards_block(cat_map, "en")
    zh_blocks = _render_cards_block(cat_map, "zh")
    return f"""<!-- 项目集：自动维护，由 zz_scripts/gen_project_wrappers.py 同步 -->

<div class="lang-en" markdown>

## Projects

<div class="grid cards" markdown>
{en_blocks}</div>

</div>

<div class="lang-zh" hidden markdown>

## 项目集

<div class="grid cards" markdown>
{zh_blocks}</div>

</div>

"""


def update_index_md(cards_text: str) -> None:
    """Replace content between INDEX_START / INDEX_END in docs/index.md."""
    original = INDEX_MD.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"({re.escape(INDEX_START)})(.*?)({re.escape(INDEX_END)})",
        re.DOTALL,
    )
    if not pattern.search(original):
        print(
            f"[gen_project_wrappers] ERROR: markers {INDEX_START} / {INDEX_END} "
            f"not found in docs/index.md",
            file=sys.stderr,
        )
        raise SystemExit(2)
    new_content = pattern.sub(
        lambda m: f"{INDEX_START} -->\n{cards_text.rstrip()}\n{INDEX_END} -->",
        original,
    )
    _atomic_write(INDEX_MD, new_content)


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------
def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    projects = discover_projects()
    written, missing = write_wrappers(projects)
    removed = cleanup_stale_wrappers(projects)
    print(f"[gen_project_wrappers] generated {len(written)} wrappers")
    if removed:
        print(f"[gen_project_wrappers] removed {len(removed)} stale wrappers")
        for r in removed[:5]:
            print(f"  - {r}")
        if len(removed) > 5:
            print(f"  ... and {len(removed) - 5} more")

    if missing:
        print(f"\nMISSING {len(missing)} sources:")
        for m in missing:
            print(f"  - {m}")
        raise SystemExit(1)

    # Update mkdocs.yml nav.
    nav_text = render_nav(projects)
    update_mkdocs_nav(nav_text)
    print(f"[gen_project_wrappers] mkdocs.yml nav: {nav_text.count(chr(10))} lines")

    # Update docs/index.md project grid section.
    cards_text = render_index_cards(projects)
    update_index_md(cards_text)
    print(f"[gen_project_wrappers] docs/index.md grid section updated")

    # Warn about README files that look like projects but weren't picked up.
    _warn_unmatched_readmes(projects)


def _warn_unmatched_readmes(projects: list[Project]) -> None:
    """Heuristic: any README.md under egs_* / ai_notes / egs_skill that
    isn't in the discovered set should be flagged so the user can add a
    DISCOVERY_RULE."""
    roots = ("egs_trade", "egs_data", "egs_alpha", "egs_llm", "egs_fin_nlp",
             "egs_online_platform", "egs_aide", "egs_skill", "ai_notes")
    matched_sources = {p.source_rel for p in projects}
    unmatched: list[Path] = []
    for r in roots:
        rp = REPO_ROOT / r
        if not rp.is_dir():
            continue
        for readme in rp.rglob("README.md"):
            try:
                rel = readme.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                continue
            # Skip pytest cache / 顶层 egs_* 总览 README（不是项目）
            parts = readme.parts
            if ".pytest_cache" in parts:
                continue
            if rel.endswith("/README.md") and len(parts) == 3:
                # egs_trade/README.md 这种顶层总览，不该暴露为项目页
                continue
            if rel not in matched_sources:
                unmatched.append(readme)
    if unmatched:
        print(f"\n[gen_project_wrappers] NOTE: {len(unmatched)} README files "
              f"under known egs roots are not covered by DISCOVERY_RULES.")
        print("  (They may be internal docs you don't want to expose; if you "
              "do want them, add a rule.)")
        for u in unmatched[:20]:
            print(f"    - {u.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()