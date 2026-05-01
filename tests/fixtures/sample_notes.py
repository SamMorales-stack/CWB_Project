"""Reusable sample meeting-note content for tests."""

NOTE_SPRINT_PLANNING = """
Sprint planning - 2026-04-29

Attendees: Alex (PM), Priya (Backend), Marco (Frontend)

Decisions:
- Priya will own the Postgres migration. Target ship date: 2026-05-06.
- Marco picks up the new dashboard skeleton. No firm date yet.
- The customer-export script that Alex started last week is now blocked
  on a billing-team API change.
""".strip()

NOTE_FOLLOWUP_EMAIL = """
Subject: Re: Sprint planning follow-up
From: priya@sj.example
Date: 2026-04-30

Quick correction from yesterday: the Postgres migration target should be
2026-05-08, not 2026-05-06. I had a calendar conflict on the original
date. Please update the tracker.
""".strip()
