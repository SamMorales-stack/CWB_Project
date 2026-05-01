SJ Project Planner Agent: Agentic AI for Task-Progress and Project Tracking
Overview
In complex delivery environments, project plans (e.g., trackers, schedules, and Gantt charts) often fall out of sync with reality because the "truth" of what changed really lives in meeting discussions, email threads, and informal updates. Teams may agree on new tasks, sequencing changes, shifting owners, or revised dates, but unless someone manually updates the plan, those decisions are not reflected in the official schedule. This creates avoidable confusion, weak governance visibility, and rework across delivery teams.

SJ is exploring how agentic AI can act as a lightweight planning assistant that converts unstructured project conversations into structured planning updates, while keeping humans in control. The goal is not to replace project controls, but to reduce the manual effort required to maintain a reliable plan and to ensure that task ownership, due dates, and priority changes are reflected quickly and consistently.

Limitations of Current Manual Approach
Task updates are discussed in meetings but are not consistently translated into the tracker or schedule.
Owners and deadlines may be agreed verbally but remain ambiguous or scattered across notes and emails.
Plans can become "stale," leading to mismatched expectations across teams and stakeholders.
Manual Gantt/plan maintenance is time-consuming and requires constant follow-up.
Priority shifts are not always captured cleanly, making it hard to see what truly changed week to week.
Dataset
Participants should create and work with a small, curated set of internal-style planning inputs such as:

meeting notes / minutes (with decisions and actions),
action logs and task trackers (sample formats),
email-style conversations containing task and date changes,
calendar-style meeting metadata (date/time/attendees),
simplified work breakdown structure (WBS) or milestone list,
a baseline plan snapshot to compare against (for "delta" detection).
Dataset: https://github.com/DoreenSteven/CWB_SJ

Research on Existing Solutions
Many generic copilots can summarise a meeting or extract action items, but fewer solutions are designed to:

reliably convert conversational updates into structured planning fields (task, owner, due date, status, dependency),
maintain a change log of what was updated and why,
compare "latest plan" vs "baseline" and highlight material schedule changes,
apply a human approval workflow before updating official trackers,
produce an executive-friendly "what changed in the plan" summary.
This makes the problem more than summarisation — it is a practical meeting-to-plan translation and governance challenge.

What Participants Need to Do
Basic Functions
Develop an AI agent that extracts from meeting notes and updates:
tasks/actions, owners, due dates, status signals (e.g., started/blocked/done), and (where present) dependencies or sequencing cues.
Consolidate extracted items into a structured tracker with a consistent schema (e.g., Task, Owner, Due Date, Status, Source, Confidence).
Detect whether each extracted item is:
a new task,
an update to an existing task, or
a potential conflict/ambiguity requiring human clarification.
Generate a "Plan Update Draft" for review (what will be changed, with supporting evidence from the source text).
Produce a simple output view (dashboard, table and/or Gantt-style visual) showing current task status, urgent tasks that need attention, and upcoming deadlines.
Advanced Functions (optional features, could be implemented 1 or more)
Build a Change Detection Agent that compares current vs previous plan snapshots and highlights material changes (date shifts, owner changes, scope additions).
Add a Priority Agent that reorders tasks based on urgency, dependencies, and risk signals.
Add a Clarification Workflow that asks targeted questions when notes are incomplete (e.g., "Who is responsible for this?" "Is the due date confirmed?").
Implement a Human-in-the-loop approval step before writing updates into the "official" plan dataset.
Recommend team member assignment as suggestions based on role tags or workload heuristics, with explicit confirmation required.
The Ultimate Goal
The ultimate goal is to create a lightweight end-to-end planning assistant that helps SJ keep project plans current by translating day-to-day delivery conversations into structured, auditable plan updates — improving schedule reliability, ownership clarity, and stakeholder confidence while reducing manual project controls effort.

Further Notes on the data set and approach:
1 project,
a curated set of meeting notes/emails (e.g., 20–50 items),
a limited task schema and status set,
and a review-before-update workflow (instead of full automation).
A strong demo is a "draft plan update" output plus a simple dashboard showing task changes and a Gantt-style view.