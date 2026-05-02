# UI Design Ideas & Color Palettes — SJ Project Planner Agent

## Stretch Features to Implement (from original spec)

### 1. Replay Mode
Load the CWB_SJ meeting notes in chronological order and hit **Play** — the Tracker and Gantt animate meeting-by-meeting showing the plan evolving. Pure demo gold for the pitch video. A "Replay demo" button on the Tracker page triggers the sequence automatically.

### 2. Bidirectional Traceability
Click any row in the Tracker → a side drawer appears showing every meeting note and change_log entry that ever touched that task. Makes the audit trail navigable, not just stored.

### 3. Change Detection Summary
Compare the current plan against the `plan_snapshots.csv` baseline from the dataset and highlight material changes (date shifts > 7 days, owner changes, scope additions). Shows up as a "vs. Baseline" tab on the Tracker.

---

## Color Palette Options

### Option A — Ocean Professional (recommended)
Clean, modern, trustworthy. Works well for enterprise/governance tools.

| Role | Color | Hex |
|---|---|---|
| Primary / brand | Deep ocean blue | `#0B4F6C` |
| Accent / CTA | Bright cyan | `#01BAEF` |
| Success / approved | Emerald green | `#20BF55` |
| Danger / rejected | Coral red | `#FB3640` |
| Warning / conflict | Amber | `#F4A261` |
| Background | Near-black | `#0E1117` |
| Surface / cards | Dark slate | `#1C2333` |
| Text | Off-white | `#E8EAF0` |

**Vibe:** Serious but energetic. Feels like a real product. The cyan accent pops on dark backgrounds.

---

### Option B — Sunrise Gradient
Warm, creative, memorable. Stands out from typical enterprise tools.

| Role | Color | Hex |
|---|---|---|
| Primary | Deep indigo | `#3D155F` |
| Accent | Vibrant purple | `#9B5DE5` |
| Secondary | Hot coral | `#F15BB5` |
| Success | Lime green | `#00BBF9` |
| Warning | Sunshine yellow | `#FEE440` |
| Background | Rich dark | `#1A1A2E` |
| Surface | Dark purple | `#16213E` |

**Vibe:** Creative and bold. More "startup" than "enterprise." Memorable for judges but may feel less serious.

---

### Option C — Forest + Earth
Calming, professional, distinctive. Unusual for data tools which tend toward blues.

| Role | Color | Hex |
|---|---|---|
| Primary | Forest green | `#2D6A4F` |
| Accent | Bright mint | `#40916C` |
| Highlight | Warm sand | `#D9A96A` |
| Danger | Terracotta | `#C84B31` |
| Success | Sage | `#80B918` |
| Background | Dark charcoal | `#1B1B1B` |
| Surface | Deep forest | `#1E2D2F` |

**Vibe:** Calm, nature-inspired, different. Good if you want to stand out from blue-dominant tools.

---

### Option D — Neon Dark (bold choice)
High-contrast, tech-forward, very modern.

| Role | Color | Hex |
|---|---|---|
| Primary | Electric blue | `#4361EE` |
| Accent | Neon purple | `#7209B7` |
| Highlight | Hot pink | `#F72585` |
| Success | Neon green | `#4CC9F0` |
| Warning | Electric yellow | `#FCA311` |
| Background | Pure black | `#0A0A0A` |
| Surface | Dark gray | `#161616` |

**Vibe:** Developer-cool, very techy. High impact but high risk — can feel harsh if not applied carefully.

---

## UI Improvement Ideas

### 1. Streamlit Theme Config
Set a global theme via `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#01BAEF"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1C2333"
textColor = "#E8EAF0"
font = "sans serif"
```

### 2. Metric Cards Row (Dashboard feel)
Add a row of 4 metric cards at the top of the Tracker page:
- **Total tasks** (count)
- **Overdue** (count, red if > 0)
- **Pending drafts** (count, amber if > 0)
- **Applied this week** (count from change_log)

```python
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tasks", 52)
col2.metric("Overdue", 8, delta="↑2 this week", delta_color="inverse")
col3.metric("Pending Drafts", 3)
col4.metric("Applied This Week", 12)
```

### 3. Status Badges Instead of Plain Text
Replace raw status text in tables with colored HTML badges:
```python
STATUS_COLORS = {
    "not_started": ("#4361EE", "#E8F0FF"),
    "in_progress": ("#F4A261", "#FFF3E0"),
    "blocked":     ("#FB3640", "#FFE8E9"),
    "done":        ("#20BF55", "#E8F9ED"),
}

def badge(status):
    fg, bg = STATUS_COLORS.get(status, ("#999", "#222"))
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600">{status}</span>'
```

### 4. Priority Indicators
Show priority as colored dots instead of text:
- 🔴 High
- 🟡 Medium
- 🟢 Low

### 5. Sidebar Improvements
- Add a project name header with a subtle logo/icon
- Show a progress ring: X% of tasks done
- Show the date of the last approved change

### 6. Gantt Improvements
- Gradient bar colors (darker = higher priority)
- Milestone markers for major deadlines
- Hover tooltips showing owner + status

### 7. Inbox — Live Preview
After the form is filled out, show a preview of the note before processing (collapsible). Reduces accidental submissions.

### 8. Animated Processing Feedback
Replace the generic spinner with a step-by-step progress display:
```
✅ Note ingested
⏳ Extracting tasks...
✅ Found 5 items
⏳ Classifying against 52 existing tasks...
✅ Draft created
```

### 9. Change Log — Diff Highlighting
Color the diff column: green for additions, red for removals, instead of plain text arrows.

### 10. Page Headers with Subtitles
Each page gets a consistent header style with a descriptive subtitle and a subtle icon.

---

## Implementation Priority

Given the extended deadline (May 10), suggested order:

| Priority | Item | Effort |
|---|---|---|
| 1 | Streamlit theme config (`.streamlit/config.toml`) | 10 min |
| 2 | Metric cards on Tracker | 30 min |
| 3 | Status badges (colored pills) | 30 min |
| 4 | Sidebar improvements (progress, last-updated) | 45 min |
| 5 | Animated processing feedback in Inbox | 45 min |
| 6 | Replay mode (stretch feature) | 2 hrs |
| 7 | Bidirectional traceability (stretch feature) | 2 hrs |
| 8 | Change Detection vs. Baseline (stretch feature) | 3 hrs |

---

## Which palette?

Tell me which option (A, B, C, D) resonates and any adjustments — I'll implement the theme and all the UI improvements in one session.
