# On-call note — Policy extraction pipeline (System 1)

*Author: Narendran Chakkrapani (n.chakkrapani@accenture.com). For whoever triages
`routing_decisions.json` at 2 a.m.*

## What a healthy run looks like
- Exit code 0, with a final JSON summary that has `decisions_written` + `escalations` = the number of
  `POL-*.txt` files in the input folder (here, 9 + 1 = 10).
- About 2 API calls per policy (extract + reviewer). Each extra call is a retry. My reference run
  made 20 calls for 10 policies, meaning one `missing_source` escalation (1 call, no review) and one
  `consistency` retry (`pipeline-run.txt`).
- A mix of `auto_approve`, `human_review` and `spot_check`. **`spot_check` > 0 needs at least one
  `auto_approve`**, because the sampler only draws from auto-approved records.

## Check these first, in order
1. **Escalations.** Look at `escalations` and `pattern_summary` in the summary. `missing_source` is
   expected (the document lacks the field), so send those to a human and don't re-run. A sudden
   jump in one `detected_pattern` (say, ten `premium_amount_absent` at once) almost always means a
   carrier changed its template. That's not a model problem.
2. **The `reason` string on each `human_review` record.** It tells you which signal fired:
   `fields_below_threshold=[...]` (model confidence < 0.90), `reviewer_disagreement=[...]`
   (independent reviewer), or integration failures. Group by field. If one field dominates (in my
   run `coverage_limit` showed up in 5 of 9 disagreements), suspect the field's definition, not
   the documents.
3. **Retries.** `validation_failed` lines followed by success are fine (format/consistency errors
   repaired). A rising retry count across runs is the earliest drift signal.

## Which signal lies
- **Model confidence.** POL-2025-002 rated every field 0.95–1.0 and the reviewer still disagreed.
  The calibration slice shows umbrella/exclusions at `conf=0.93 acc=0.00`. Never auto-approve on
  confidence alone, and never "fix" a queue by lowering the threshold.
- **The overall Brier score.** `OVERALL brier=0.291` looks moderate while one cell sits at 0.865.
  Always read the sliced report.
- **An empty spot-check list.** It looks like "nothing to audit", but it can mean nothing was
  auto-approved at all (0 / 9 / 0 in my run).

## What not to do
- Don't re-run a `missing_source` escalation hoping it passes. A pass on re-run means the model
  invented the value.
- Don't edit `routing_decisions.json` by hand. Re-route by re-running with the same `--seed` so the
  spot-check sample is reproducible.
