"""Shared design system helpers and CSS for PlanForge by SJ."""
from __future__ import annotations

import streamlit as st

# ── Design Tokens ──────────────────────────────────────────────────────────

COLORS = {
    "bg": "#0B0F19",
    "surface": "#111827",
    "surface_hi": "#1F2937",
    "border": "#374151",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "accent": "#3B82F6",
    "success": "#2DD4BF",
    "warning": "#FBBF24",
    "error": "#F87171",
    "text": "#F9FAFB",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
    "logo_red": "#EF4444",
}

STATUS_PALETTE = {
    "not_started": ("#64748B", "rgba(100,116,139,0.12)"),
    "in_progress": ("#2563EB", "rgba(37,99,235,0.12)"),
    "blocked": ("#F87171", "rgba(248,113,113,0.12)"),
    "done": ("#2DD4BF", "rgba(45,212,191,0.12)"),
    "conflict": ("#FBBF24", "rgba(251,191,36,0.12)"),
}

STATUS_LABELS = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "blocked": "Blocked",
    "done": "Done",
    "conflict": "Conflict",
}

PRIORITY_PALETTE = {
    "high": "#F87171",
    "medium": "#FBBF24",
    "low": "#2DD4BF",
}

OP_PALETTE = {
    "create": "#2DD4BF",
    "update": "#2563EB",
    "delete": "#F87171",
    "conflict": "#FBBF24",
}

OP_LABELS = {
    "create": "Create",
    "update": "Update",
    "delete": "Delete",
    "conflict": "Conflict",
}

ICONS = {
    "inbox": "📥",
    "drafts": "📝",
    "tracker": "📊",
    "gantt": "📅",
    "changelog": "🕘",
    "replay": "🔄",
    "tasks": "⏹",
    "overdue": "⚠",
    "pending": "⏳",
    "applied": "✦",
    "high_conf": "●",
    "med_conf": "●",
    "low_conf": "●",
    "total": "⏹",
    "success": "✔",
    "error": "✕",
    "warning": "⚠",
    "info": "ℹ",
    "postgres": "DB",
    "llm": "AI",
    "merge": "⇋",
    "separate": "＋",
    "today": "📍",
}

APP_NAME = "PlanForge"
APP_TAGLINE = "by SJ"
APP_PAGE_TITLE = "PlanForge by SJ"


# ── SJ Logo ────────────────────────────────────────────────────────────────

def sj_logo_html(size: int = 36) -> str:
    """Return a CSS-only SJ logo as HTML."""
    dot_size = int(size * 0.2)
    top_offset = int(size * 0.17)
    right_offset = int(size * 0.19)
    font_size = int(size * 0.44)
    return (
        f'<div style="display:inline-flex;flex-shrink:0;width:{size}px;height:{size}px;'
        f'border-radius:8px;background:{COLORS["primary"]};align-items:center;'
        f'justify-content:center;position:relative;vertical-align:middle;">'
        f'<span style="color:#fff;font-size:{font_size}px;font-weight:800;'
        f'letter-spacing:-0.02em;line-height:1;">Sj</span>'
        f'<div style="position:absolute;width:{dot_size}px;height:{dot_size}px;'
        f'border-radius:50%;background:{COLORS["logo_red"]};top:{top_offset}px;'
        f'right:{right_offset}px;box-shadow:0 0 0 2px rgba(239,68,68,0.25);"></div>'
        f'</div>'
    )


# ── Global CSS Injection ───────────────────────────────────────────────────

def inject_global_css() -> None:
    """Inject custom CSS to override Streamlit defaults."""
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        background: {COLORS["bg"]} !important;
    }}

    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: {COLORS["surface"]}; }}
    ::-webkit-scrollbar-thumb {{ background: {COLORS["border"]}; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLORS["text_muted"]}; }}

    [data-testid="stSidebar"] {{
        background: {COLORS["surface"]} !important;
        border-right: 1px solid {COLORS["border"]} !important;
    }}
    [data-testid="stSidebar"] .stRadio > div {{
        display: flex; flex-direction: column; gap: 4px;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        background: transparent; border-radius: 8px;
        padding: 8px 12px; margin: 0;
        transition: all 0.15s ease;
        color: {COLORS["text_secondary"]} !important;
        font-weight: 500; font-size: 14px;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: {COLORS["surface_hi"]};
        color: {COLORS["text"]} !important;
    }}
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + label {{
        background: {COLORS["surface_hi"]} !important;
        color: {COLORS["primary"]} !important;
        font-weight: 600;
        border-left: 3px solid {COLORS["primary"]};
    }}

    .stButton > button {{
        border-radius: 8px !important; font-weight: 700 !important;
        font-size: 13px !important; transition: all 0.15s ease !important;
        border: 1px solid transparent !important;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS["primary"]}, {COLORS["primary_hover"]}) !important;
        box-shadow: 0 2px 8px rgba(37,99,235,0.30) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        box-shadow: 0 4px 16px rgba(37,99,235,0.45) !important;
        transform: translateY(-1px);
    }}
    .stButton > button[kind="secondary"] {{
        background: {COLORS["surface_hi"]} !important;
        border-color: {COLORS["border"]} !important;
        color: {COLORS["text_secondary"]} !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        border-color: {COLORS["primary"]} !important;
        color: {COLORS["text"]} !important;
    }}

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > input {{
        background: {COLORS["surface"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
        color: {COLORS["text"]} !important; font-size: 14px !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus,
    .stDateInput > div > div > input:focus {{
        border-color: {COLORS["primary"]} !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.15) !important;
    }}

    .stFileUploader > div > div {{
        background: {COLORS["surface"]} !important;
        border: 2px dashed {COLORS["border"]} !important;
        border-radius: 12px !important;
    }}
    .stFileUploader > div > div:hover {{ border-color: {COLORS["primary"]} !important; }}

    .streamlit-expanderHeader {{
        background: {COLORS["surface"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 10px !important;
        font-weight: 600 !important; font-size: 14px !important;
        color: {COLORS["text"]} !important;
    }}
    .streamlit-expanderContent {{
        background: {COLORS["bg"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
    }}

    .stDataFrame {{
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 12px !important; overflow: hidden !important;
    }}
    .stDataFrame thead tr th {{
        background: {COLORS["surface"]} !important;
        color: {COLORS["text_secondary"]} !important;
        font-weight: 700 !important; font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        border-bottom: 1px solid {COLORS["border"]} !important;
    }}
    .stDataFrame tbody tr td {{
        background: {COLORS["bg"]} !important;
        color: {COLORS["text"]} !important;
        font-size: 13px !important;
        border-bottom: 1px solid rgba(55,65,81,0.4) !important;
    }}
    .stDataFrame tbody tr:hover td {{ background: {COLORS["surface"]} !important; }}

    [data-testid="stMetric"] {{
        background: {COLORS["surface"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 12px !important; padding: 16px !important;
    }}
    [data-testid="stMetric"] label {{
        color: {COLORS["text_secondary"]} !important;
        font-size: 12px !important; font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    [data-testid="stMetric"] > div {{
        color: {COLORS["text"]} !important;
        font-size: 28px !important; font-weight: 800 !important;
    }}

    .stAlert {{ border-radius: 10px !important; border: 1px solid !important; }}
    .stAlert [data-baseweb="notification"] {{ background: {COLORS["surface"]} !important; }}
    .stSpinner > div {{ color: {COLORS["primary"]} !important; }}
    hr {{ border-color: {COLORS["border"]} !important; margin: 24px 0 !important; }}
    .stCheckbox > label {{ color: {COLORS["text_secondary"]} !important; font-size: 13px !important; }}
    .stCaption {{ color: {COLORS["text_muted"]} !important; font-size: 13px !important; }}
    .stSubheader {{
        color: {COLORS["text"]} !important; font-weight: 700 !important;
        font-size: 16px !important; margin-top: 24px !important; margin-bottom: 12px !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ── HTML Component Helpers ─────────────────────────────────────────────────

def status_badge(status: str) -> str:
    """Return a pill-style HTML status badge."""
    fg, bg = STATUS_PALETTE.get(status, (COLORS["text_secondary"], "rgba(156,163,175,0.12)"))
    label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:700;background:{bg};color:{fg};'
        f'border:1px solid {fg}33;letter-spacing:0.02em;text-transform:capitalize;">'
        f'{label}</span>'
    )


def op_badge(op: str) -> str:
    """Return a pill-style HTML operation badge."""
    color = OP_PALETTE.get(op, COLORS["text_secondary"])
    label = OP_LABELS.get(op, op.upper())
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:700;background:{color}15;color:{color};'
        f'border:1px solid {color}33;letter-spacing:0.02em;">'
        f'{label}</span>'
    )


def confidence_badge(conf: float) -> str:
    """Return a confidence badge with color coding."""
    if conf >= 0.8:
        color = COLORS["success"]
        label = "High"
    elif conf >= 0.5:
        color = COLORS["warning"]
        label = "Med"
    else:
        color = COLORS["error"]
        label = "Low"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;'
        f'background:{color}15;color:{color};border:1px solid {color}33;">'
        f'{label} ({conf:.0%})</span>'
    )


def priority_dot(priority: str) -> str:
    """Return a colored dot for priority."""
    color = PRIORITY_PALETTE.get(priority, COLORS["text_muted"])
    return f'<span style="color:{color}">●</span>'


def card(title: str | None = None, content: str = "", border_color: str | None = None) -> str:
    """Return a styled card HTML string."""
    bc = border_color or COLORS["border"]
    header = ""
    if title:
        header = (
            f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;">'
            f'{title}</div>'
        )
    return (
        f'<div style="background:{COLORS["surface"]};border:1px solid {bc};'
        f'border-radius:12px;padding:16px;margin:8px 0;">'
        f'{header}{content}</div>'
    )


def metric_card_html(label: str, value: str, icon: str = "", color: str | None = None) -> str:
    """Return a custom metric card HTML."""
    c = color or COLORS["text"]
    return (
        f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
        f'border-radius:12px;padding:20px;text-align:left;">'
        f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_secondary"]};'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">'
        f'{icon} {label}</div>'
        f'<div style="font-size:32px;font-weight:800;color:{c};line-height:1;">'
        f'{value}</div></div>'
    )


def section_header(title: str, subtitle: str = "") -> None:
    """Render a consistent section header."""
    st.markdown(
        f"<div style='margin-top:28px;margin-bottom:16px;'>"
        f"<div style='font-size:20px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;'>"
        f"{title}</div>"
        f"<div style='font-size:13px;color:{COLORS['text_muted']};margin-top:4px;'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, subtitle: str) -> None:
    """Render a centered empty state."""
    st.markdown(
        f"<div style='text-align:center;padding:60px 20px;'>"
        f"<div style='font-size:48px;margin-bottom:16px;'>{icon}</div>"
        f"<div style='font-size:18px;font-weight:700;color:{COLORS['text_secondary']};margin-bottom:8px;'>"
        f"{title}</div>"
        f"<div style='font-size:14px;color:{COLORS['text_muted']};'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def connection_pill(name: str, connected: bool) -> str:
    """Return a small connection status pill."""
    color = COLORS["success"] if connected else COLORS["error"]
    dot = "●"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'font-size:10px;font-weight:700;color:{color};background:{color}12;'
        f'padding:3px 8px;border-radius:6px;">{dot} {name}</span>'
    )


def timeline_item(
    time_str: str,
    op: str,
    diff: str,
    evidence: str,
    approved_by: str,
) -> str:
    """Return a timeline-style change-log item."""
    op_color = OP_PALETTE.get(op, COLORS["text_secondary"])
    op_label = OP_LABELS.get(op, op.upper())
    return (
        f'<div style="display:flex;gap:16px;margin:12px 0;">'
        f'  <div style="display:flex;flex-direction:column;align-items:center;">'
        f'    <div style="width:10px;height:10px;border-radius:50%;background:{op_color};'
        f'    box-shadow:0 0 0 4px {op_color}22;"></div>'
        f'    <div style="width:2px;flex:1;background:{COLORS["border"]};"></div>'
        f'  </div>'
        f'  <div style="flex:1;background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
        f'  border-radius:10px;padding:14px;margin-bottom:8px;">'
        f'    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'      <span style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
        f'      text-transform:uppercase;letter-spacing:0.05em;">{time_str}</span>'
        f'      {op_badge(op)}'
        f'    </div>'
        f'    <div style="font-size:13px;color:{COLORS["text"]};margin-bottom:6px;">{diff}</div>'
        f'    <div style="font-size:12px;color:{COLORS["text_secondary"]};margin-bottom:4px;">'
        f'    <em>{evidence}</em></div>'
        f'    <div style="font-size:11px;color:{COLORS["text_muted"]};">Approved by {approved_by}</div>'
        f'  </div>'
        f'</div>'
    )
