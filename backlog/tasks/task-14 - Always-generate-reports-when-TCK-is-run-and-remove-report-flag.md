---
id: TASK-14
title: Always generate reports when TCK is run and remove --report flag
status: Done
assignee: []
created_date: '2026-03-12 08:49'
updated_date: '2026-03-12 08:52'
labels:
  - enhancement
  - reporting
  - docs
dependencies: []
references:
  - run_tck.py
  - .agents/skills/run-tck/SKILL.md
  - .agents/skills/diagnose-failure/SKILL.md
  - AGENTS.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently, reports (compatibility HTML/JSON, pytest-html, JUnit XML) are only generated when `--report` is passed to `run_tck.py`. Reports should always be generated on every TCK run, making `--report` unnecessary.

**Changes needed:**

1. **`run_tck.py`**: Remove the `--report` flag and always pass `--compatibility-report`, `--html`, `--self-contained-html`, and `--junitxml` to pytest
2. **Skills**: Update all skill files that mention `--report`:
   - `.agents/skills/run-tck/SKILL.md` — remove `--report` from all example commands
   - `.agents/skills/diagnose-failure/SKILL.md` — check for `--report` references
   - Any other skills referencing the flag
3. **Docs**: Update `AGENTS.md` if it mentions `--report`
4. **README or other docs**: Search for `--report` references across the codebase
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reports (compatibility HTML/JSON, tck_report.html, junitreport.xml) are generated on every TCK run without needing --report
- [x] #2 The --report flag is removed from run_tck.py
- [x] #3 All skills and documentation are updated to remove --report references
- [x] #4 Running `uv run ./run_tck.py --sut-host <host>` produces reports in the reports/ directory
<!-- AC:END -->
