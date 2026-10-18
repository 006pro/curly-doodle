# Reflection Brief — Evaluation and Observability Capstone

**Name:** Narendran Chakkrapani (n.chakkrapani@accenture.com)
**Date:** 2026-10-18

> Ground every answer in your own run. When a question asks for a number, file name, or line, paste
> it from your artifacts — a reviewer should be able to find it. Answers that are correct in the
> abstract but cite nothing do not meet the bar. Keep it short and specific.

All paths below are relative to the root of this evidence pack (the repository root).

---

## 0. Environment

| Field | Value |
|---|---|
| OS & version | Microsoft Windows [Version 10.0.26200.9711] (Windows 11 Pro), see `environment.txt` |
| Python version | Python 3.11.9 |
| Date run | 2026-10-18 |
| Ran any system live? (which) | Yes. System 1: full `pipeline` run plus both perturbation `extract` runs. System 2: one `--mode record` perturbation run. Live calls went through the course's Vocareum endpoint (`environment.txt` deviation #3). System 3 ran `--offline`. |

---

## 1. Validated, routed pipeline

| Evidence | Value |
|---|---|
| Passing test count | `45 passed, 3 skipped in 0.15s` (`01-policy-pipeline/tests.txt`) |
| Routing output file | `01-policy-pipeline/routing_decisions.json` (9 records) |
| auto_approve / human_review / spot_check counts | 0 / 9 / 0, plus `"escalations": 1` (`01-policy-pipeline/pipeline-run.txt`) |

**1a. Retry boundary.** From your perturbation run (a required field removed), paste the escalation
record. How many API calls did the system make, and why is retrying a futile case worse than
escalating it?

> From `perturbations/s1-extract-no-premium.txt` (POL-2025-001 with its `Total Policy Premium` line
> deleted):
> ```
> "category": "missing_source", "detected_pattern": "premium_amount_absent", "field": "premium_amount",
> "kind": "escalation", "reason": "Field 'premium_amount' returned null — the source document does not
> contain this information. Retry is futile; escalate to human review."
> ```
> It made **one** API call: the file has a single `POST https://claude.vocareum.com/v1/messages` line
> before `validation_failed`. The same happened inside the batch: POL-2025-009
> (`endorsements_absent`, `missing_source`) used one call and never reached the reviewer
> (`pipeline-run.txt` line 27).
>
> Retrying is worse than escalating for two reasons. First, the error feedback has nothing to act
> on: the information isn't in the document, so every extra attempt costs tokens and latency to
> produce the same null. Second, and more important, a retry loop that keeps saying "premium_amount
> is required" pressures the model until it *invents* a plausible premium. A futile case that
> "succeeds" on retry is a fabrication with a clean validation history. The recoverable case shows
> what retries are actually for: POL-2025-010 failed on `consistency`
> (`premium_does_not_match_components`), was retried with the error appended, and passed on its
> second extraction attempt (`pipeline-run.txt` lines 29–31). The system spends retries only where
> the feedback can change the answer.

**1b. Reading the router.** Pick one `human_review` record from your routing output. Which of the
three signals (confidence, reviewer, integration) sent it to a human? If you had trusted the model's
confidence alone, what would have happened?

> **POL-2025-002** (auto) in `01-policy-pipeline/routing_decisions.json`:
> `"confidence_summary": {"coverage_limit": 1.0, "deductible": 0.95, "endorsements": 0.95,
> "exclusions": 0.95, "policy_type": 1.0, "premium_amount": 1.0}`, `"fields_below_threshold": []`,
> `"integration_failures": []`, `"reason": "reviewer_disagreement=['coverage_limit', 'deductible']"`.
> The independent reviewer was the only signal. Every field cleared the 0.90 threshold, and
> integration was clean.
>
> With confidence alone, POL-2025-002 would have been **auto-approved**, and so would six of the
> nine records. Only POL-2025-001, -003 and -007 had a field under 0.90. POL-2025-007 is the
> mirror case: `"reason": "fields_below_threshold=['deductible']"` with `"reviewer_disagreements": []`.
> So each signal catches cases the other misses, which is why the router ANDs all three.
>
> My live run is also a lesson in reading the router as a whole. The result was 0 auto-approve and
> 9 human-review, and with no auto-approvals the stratified sampler had nothing to spot-check
> (`"spot_check": 0`). The reviewer disagreed on `coverage_limit` for 5 of 9 policies (001–005). That
> clustering points to a schema ambiguity rather than random noise: multi-limit coverage such as
> `$100,000 / $300,000` is forced into one number, and the extractor returned `"coverage_limit": 100000`
> (`perturbations/s1-extract-original.txt`). I'd fix that field definition before tuning any
> threshold.

**1c. Where the aggregate lies.** Run the calibration snippet. Quote the one cell whose accuracy lags
its confidence, plus the overall figure. What does slicing by `policy_type × field` catch that a
single number hides?

> From `01-policy-pipeline/calibration-report.txt`:
> `umbrella  exclusions      n=2 conf=0.93 acc=0.00 brier=0.865` and `OVERALL brier=0.291`.
>
> Taken alone, 0.291 reads as "moderately calibrated" (4 of 6 labels correct). The slice shows
> that the error isn't spread evenly. It sits entirely in one cell, where the model is **wrong every
> time while claiming 93% confidence**, and the healthy `auto premium_amount` cell (n=3,
> brier=0.003) dilutes it. A single number would let you raise the auto-approve threshold for
> everything or for nothing. The slice tells you to route umbrella/exclusions to a human, however
> confident the model is, and leave the rest alone. It also shows how small each cell is (n=2, n=1),
> which is a warning in itself about trusting any of these numbers.

---

## 2. Schema-enforced two-pass extraction

| Evidence | Value |
|---|---|
| Passing test count | `25 passed in 2.30s` (`02-mortgage-extraction/tests.txt`) |
| Document run | `fixtures/documents/appraisal_informal_sqft.txt --mode replay` (`02-mortgage-extraction/extract-run.txt`) |
| Classified type | `type=appraisal` → `tool=extract_appraisal` (both income docs: `type=income_verification`) |

**2a. Two guarantees.** Paste your discrepancy-run output. Tool use already forces valid JSON, yet the
validator still catches a bad sum. Why are these two different guarantees? Name one error each cannot
catch.

> From `02-mortgage-extraction/discrepancy-run.txt` (`income_sum_mismatch.txt`, exit code 1):
> ```
> "validation": { "consistent": false, "discrepancies": [ { "field": "total_monthly_income",
>   "calculated": 9642.17, "stated": 10892.17, "delta": -1250.0 } ] }
> ```
> Forced `tool_choice` plus the JSON Schema guarantees **shape**: every field is present and
> correctly typed, so `"stated_monthly_total": 10892.17` is a number and not the string
> "10,892.17". It says nothing about whether the values agree with each other. The validator
> guarantees a **relationship**: the five line items must add up to the stated total. Here they
> don't, and the delta of −1,250.00 is exactly `"bonus_monthly": 1250.0`, which suggests the
> document's own total counts the bonus twice. The extractor copied the document faithfully, and
> only arithmetic caught the problem.
>
> *What schema enforcement cannot catch:* the bad sum above, which is perfectly valid JSON.
> *What the validator cannot catch:* a value that is internally consistent but false. My live
> perturbation shows one (`perturbations/s2-corrected-total-record.txt`). The model emitted
> `"loan": {"amount": 0.0, ...}` and `"address": "<UNKNOWN>"` for a paystub, and the result was still
> `"consistent": true`. No sum involves `loan.amount`, so a fabricated zero passes both checks.

**2b. Refusing to fabricate.** Run on a document missing a field. Paste that field's output. Why null
instead of an invented value? Point to the schema choice that allows it.

> From `02-mortgage-extraction/missing-field-run.txt` (`income_missing_bonus.txt`):
> `"base_monthly": 5673.08, "bonus_monthly": null, ... "stated_monthly_total": null`. The paystub's
> EARNINGS block lists only `Regular Salary 5,673.08`, `Holiday Pay 0.00` and `PTO - Vacation 0.00`,
> with no bonus line.
>
> `null` means "the document is silent". `0.0` would mean "the document says the bonus is zero".
> Underwriting treats those differently: a missing bonus triggers a request for documentation,
> while a fabricated zero (or an invented figure) quietly changes qualifying income. The schema
> allows this with the nullable union `"bonus_monthly": {"type": ["number", "null"]}`
> (`mortgage_extractor/schema.py:104`). The field is also kept out of the `required` lists, and
> prompt rule 1 says "Return null for any field not explicitly stated in the document. Do not infer,
> default, or fabricate." (`prompts.py:26`). My live drift run proves the point from the other
> side. Where the schema did **not** allow null (`"amount": {"type": "number"}`, schema.py:85, and
> `"address": {"type": "string"}`, schema.py:58), the model filled in `0.0` and `"<UNKNOWN>"` as soon
> as it decided to emit those sections. A non-nullable field forces a guess.

**2c. Normalization.** Quote one field where the source text and extracted value differ in format
("about 2,400 sq ft" → `2400`). Why normalize at extraction time rather than downstream?

> Source (`appraisal_informal_sqft.txt` line 37): `Gross Living Area:   approximately 2,400 sq ft
> (above-grade finished)`. Extracted (`02-mortgage-extraction/extract-run.txt`):
> `"gross_living_area_sqft": 2400`, typed `["integer", "null"]` in the schema.
>
> At extraction time the model can still see the context needed to choose the right number. The
> same document also mentions `~900 sq ft total` basement, a `441 sq ft` garage and a lot of
> `approx. 20,037 sq ft`, and only the above-grade figure is GLA. A downstream parser would get a
> bare string like "approximately 2,400 sq ft" with that context gone. Every consumer (the
> validator, the comparables check, the LTV math) would need its own fragile parser, and each could
> disagree with the others. Normalizing once, against a typed schema, gives every later check a
> number it can compare.

---

## 3. Multi-source synthesis

| Evidence | Value |
|---|---|
| Passing test count | `34 passed, 2 warnings in 26.92s` (`03-supply-chain/tests.txt`) |
| Briefing file | `03-supply-chain/briefing.md` (run log: `03-supply-chain/investigation-run.txt`) |
| Section the conflict landed in | **Contested**: `on_time_delivery_rate  _[2 sources, conflicting]_  ⚠️ ESCALATE` |

**3a. Annotate, don't arbitrate.** Quote one conflicting-metric pair from your briefing — both values,
sources, dates. Give one way a reader is better served by the preserved conflict than by a single
reconciled number.

> From `03-supply-chain/briefing.md`, Contested section:
> `95.0 percent — supplier_audit (as of 2026-04-10)` vs `78.0 percent — logistics (as of 2026-04-05)`,
> flagged `escalation: high-impact metric is contested across sources`.
>
> A reconciled number such as an 86.5% average describes a delivery rate that nobody measured, and
> it hides the most useful fact: the supplier's own audit and the carrier's shipment data disagree
> by 17 points. With both values kept, a reader can act on the *source*. Self-reported audits
> overstate, and the logistics feed also reports `late_shipment_count  11.0 shipments`, which
> supports the lower figure. The reader can ask Meridian for shipment-level data before renewing,
> instead of signing off on a number that splits the difference. The synthesis is deterministic
> Python, so the guarantee doesn't rely on a prompt: "conflicts are annotated, not arbitrated
> — every conflicting value is kept with its source and date" (`synthesis.py` docstring).

**3b. Source goes dark.** Run with `--simulate-timeout`. Paste the part of the briefing showing the
failed source. How is "unreachable" handled differently from "nothing to report," and why does the run
still finish?

> From `03-supply-chain/briefing-timeout.md` (run log `timeout-run.txt`, `[exit code: 0]`):
> ```
> > Sources unavailable: logistics unavailable (timeout)
> ## Incomplete
> ### late_shipment_count  _[missing source: timeout reading logistics]_
> ### production_capacity_utilization  _[missing source: no source reported this metric]_  ⚠️ ESCALATE
> ```
> The two Incomplete entries put the difference side by side. `late_shipment_count` is
> **unreachable**: a source that normally reports it failed, so the reason names the source and the
> failure type ("timeout reading logistics"), and the banner names the dead source. Re-running later
> may fill it in. `production_capacity_utilization` is **nothing to report**: every source answered
> and none mentioned it, which is a real coverage gap. The run finishes because each reader returns
> a `ReaderResult` (`ok` / `error`) instead of raising. The coordinator builds the briefing from the
> successful claims and records each failed reader as `"<source> unavailable (<failure_type>)"`
> (`coordinator.py` lines 64–73). One dead source shouldn't throw away the other three.
>
> My diff (`perturbations/s3-timeout-diff.txt`) shows a cost to this: `on_time_delivery_rate` moved
> from Contested to Well-Established `_[single source only]_` at `95.0 percent — supplier_audit`, and
> its escalation disappeared. The cause is that only metrics in `EXCLUSIVE_METRICS` for the failed
> source become Incomplete (`coordinator.py` line 72), and the audit also reports on-time delivery.
> The banner is the only remaining sign that the 78% exists.

**3c. Dates as a guardrail.** Quote two claims about the same supplier with different dates. How does
requiring a date stop a time difference from reading as a contradiction?

> From `03-supply-chain/briefing.md`: `180.0 ppm — supplier_audit (as of 2026-04-10)` and
> `190.0 ppm — internal_quality (as of 2026-04-08)` for `defect_rate_ppm`. The on-time pair is
> also dated: 95% as of 2026-04-10 vs 78% as of 2026-04-05.
>
> `source_date` is a required field on every `Claim` (`models.py:31`, `source_date: date`, with no
> default), so no value can enter the briefing without its as-of date. That lets the reader tell
> "two sources disagree about the same moment" apart from "the metric moved between two
> measurements". 180 vs 190 ppm two days apart is within the 10% `REL_TOL` and reads as
> corroboration. For 95% vs 78%, the dates show the higher figure is the *newer* one. That's
> consistent with a recovery after the `March 16, 2026` Long Beach strike reported in the same
> briefing, and inconsistent with "the audit is just wrong". The code classifies by value
> tolerance, not by date. The date's job is to keep the *human* from misreading a time difference
> as a contradiction, or the reverse.

---

## 4. Synthesis

**4a. One principle.** Name the single moment in your runs (system + artifact) where *evaluate the
output, don't trust the model's word* most clearly caught something a trusting design would have
shipped.

> System 2, `02-mortgage-extraction/discrepancy-run.txt`. The extraction was perfect by every
> model-facing measure: correct document type (`type=income_verification`), schema-valid JSON, and
> every line item copied exactly from the paystub. A trusting design would have shipped
> `"stated_monthly_total": 10892.17` to underwriting, which is $1,250/month of qualifying income that
> doesn't exist. The deterministic check `"calculated": 9642.17, "stated": 10892.17, "delta": -1250.0`
> caught it, and asking the model whether it was sure never would have.

**4b. Confidence ≠ correctness.** Pick the system where this mattered most, and explain why using
something you observed.

> System 1. In the calibration report the model is 0.93 confident on umbrella/exclusions with
> `acc=0.00`. In my live routing output, POL-2025-002 rated every field at 0.95–1.0 and the
> independent reviewer still disagreed on `coverage_limit` and `deductible`. Six of nine policies
> would have auto-approved on confidence alone. Self-rated confidence measures how the document
> *felt* to the model, not whether the answer matched the source. That's why the router treats
> confidence as one of three AND-ed signals and gives it no veto, and why calibration has to be
> measured per `policy_type × field` against labels instead of being read off the model's own
> numbers.

**4c. Apply it.** Describe a real workflow where an LLM pulls structured results from messy input.
Which pattern — validated retry with escalation, independent review with deterministic routing, or
provenance-preserving conflict annotation — would you reach for first, and what would you instrument
to know when it broke?

> Workflow: extracting rate cards and statement-of-work terms (roles, day rates, hours, milestone
> totals, payment terms) from client and vendor PDFs into a delivery-finance system. The documents
> are scanned, multi-column and inconsistent, much like these policy renewals.
>
> I'd reach for **validated retry with escalation** first, with arithmetic validators (rate × hours
> = line total, line totals = SOW total) and a `missing_source` category that escalates instead of
> retrying. Most of the costly errors here are sums that don't reconcile and terms that are
> genuinely absent, the same pair of failures as POL-2025-010 vs POL-2025-009 in my run. Once volume
> grows, I'd add independent review with deterministic routing for the high-value contracts.
>
> Instrumentation, in priority order:
> 1. Escalation rate by `category` and `detected_pattern`, per client template. A spike in
>    `missing_source` usually means a template changed, not that the model got worse.
> 2. Retry-count distribution and first-pass success rate.
> 3. Validator discrepancy rate.
> 4. A scheduled live-vs-recorded diff on a fixed golden set. My `--mode record` run drifted from
>    its fixture (`"loan": null` became `"amount": 0.0`), and nothing else in the pipeline would have
>    flagged it.
> 5. A sliced calibration report refreshed from human-review outcomes, so a bad cell shows up
>    before the aggregate moves.
