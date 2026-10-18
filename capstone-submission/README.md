# Evidence Pack — Evaluation and Observability Capstone

**Author:** Narendran Chakkrapani (n.chakkrapani@accenture.com) · **Date:** 2026-10-18

This pack covers four phases for three reference systems: reproduce, run, perturb and reflect. Every
value quoted in `reflection-brief.md` and `perturbation-log.md` can be found in the file it cites.
Setup and the deviations from the stock instructions (TLS bundle, short venv paths on Windows, the
course API endpoint) are recorded in `environment.txt`.

## Results at a glance

| System | Tests | mypy / ruff | Key run result |
|---|---|---|---|
| 1 Policy pipeline | 45 passed, 3 skipped | no issues / all passed | live: 0 auto_approve / 9 human_review / 0 spot_check, 1 escalation |
| 2 Mortgage extraction | 25 passed | no issues / all passed | discrepancy `calculated 9642.17` vs `stated 10892.17` |
| 3 Supply chain | 34 passed | no issues / all passed | on-time 95% (audit) vs 78% (logistics) → Contested; timeout run exits 0 |

## Checklist → file

| Checklist item | Where |
|---|---|
| `environment.txt`: Python version and OS | `environment.txt` |
| Each system: full `pytest` + `mypy`/`ruff` | `0X-*/tests.txt`, `0X-*/static-checks.txt` |
| System 1: `routing_decisions.json` + calibration | `01-policy-pipeline/routing_decisions.json`, `pipeline-run.txt`, `calibration-report.txt` (offline backup: `routing-tests.txt`) |
| System 2: the three `mortgage-extract` runs | `02-mortgage-extraction/extract-run.txt` (sq ft), `missing-field-run.txt` (null), `discrepancy-run.txt` (sum) |
| System 3: briefing + `--simulate-timeout` run | `03-supply-chain/briefing.md`, `investigation-run.txt`, `briefing-timeout.md`, `timeout-run.txt` |
| `perturbation-log.md`: one experiment per system | `perturbation-log.md`, evidence in `perturbations/` |
| `reflection-brief.md`: every answer grounded | `reflection-brief.md` |
| At least one screenshot per system | `01-policy-pipeline/screenshots/` (2), `02-mortgage-extraction/screenshots/` (1), `03-supply-chain/screenshots/` (1) |

## Layout

```
capstone-submission/
├── README.md                 this index
├── environment.txt           OS, Python, venv setup, deviations
├── reflection-brief.md       completed brief
├── perturbation-log.md       one experiment per system
├── 01-policy-pipeline/
│   ├── tests.txt  static-checks.txt  routing-tests.txt
│   ├── pipeline-run.txt  routing_decisions.json  calibration-report.txt
│   ├── on-call-note.md       stand-out: 2 a.m. runbook
│   └── screenshots/          tests-and-calibration.png, perturbation-missing-premium-escalation.png
├── 02-mortgage-extraction/
│   ├── tests.txt  static-checks.txt
│   ├── extract-run.txt  missing-field-run.txt  discrepancy-run.txt
│   └── screenshots/          discrepancy-run.png
├── 03-supply-chain/
│   ├── tests.txt  static-checks.txt
│   ├── investigation-run.txt  briefing.md  timeout-run.txt  briefing-timeout.md
│   └── screenshots/          timeout-run.png
├── perturbations/
│   ├── inputs/               perturbed copies + .diff vs originals
│   ├── recorded/             live recordings created by System 2 --mode record
│   ├── s1-extract-original.txt  s1-extract-no-premium.txt  s1-retry-tests.txt
│   ├── s2-corrected-total-record.txt
│   └── s3-timeout-diff.txt
└── tools/
    └── live_shim.py          maps model alias → snapshot for the course API proxy (see environment.txt)
```

## Stand-out items
- **Live vs. recorded drift (System 2).** The live `--mode record` run returned `"loan": {"amount": 0.0}`
  and `"address": "<UNKNOWN>"`, where the recorded fixture has `null` sections, and the validator
  still passed it. This is discussed in the perturbation log and in reflection 2a/2b/4c.
- **Self-designed perturbations.** System 2 *repairs* a broken total to test whether the validator
  responds to the arithmetic. System 3's diff shows the contested metric silently becoming
  "single source only" when a source times out.
- **On-call runbook** for System 1: `01-policy-pipeline/on-call-note.md`.
