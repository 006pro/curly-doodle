# Perturbation Log

**Name:** Narendran Chakkrapani (n.chakkrapani@accenture.com)
**Date:** 2026-10-18

For each system, make one deliberate change to an input or configuration, predict the outcome, run
it, and record what actually happened. All perturbed inputs are copies in `perturbations/inputs/`
(with a `.diff` against the original). The shipped `data/` and `fixtures/` are unchanged.

---

### System 1 — validated, routed pipeline

- **Change I made (file + what I changed):** I copied `data/policies/POL-2025-001.txt` to
  `perturbations/inputs/POL-2025-001-no-premium.txt` and deleted the only line that states the
  premium, `Total Policy Premium ........................  $ 1,847.62` (see
  `perturbations/inputs/POL-2025-001.diff`). The premium is now genuinely absent, so there is no
  formatting problem for a retry to fix.
- **Command I ran (live API):**
  `policy-extractor extract ../../../capstone-submission/perturbations/inputs/POL-2025-001-no-premium.txt --policy-id POL-2025-001`
  (through `tools/live_shim.py`, see `environment.txt` #3). The control run used the same command on
  `data/policies/POL-2025-001.txt`.
- **What I predicted:** the model returns `premium_amount: null`, and the validator classifies it as
  `missing_source`. The retry loop stops after the first attempt with a `RetryFutileEscalation`, so
  there is exactly one API call and no invented premium.
- **What actually happened (paste the key output line):** from `perturbations/s1-extract-no-premium.txt`:
  ```
  2026-10-18 15:35:25,088 INFO HTTP Request: POST https://claude.vocareum.com/v1/messages "HTTP/1.1 200 OK"
  2026-10-18 15:35:25,099 INFO validation_failed
    "category": "missing_source",
    "detected_pattern": "premium_amount_absent",
    "kind": "escalation",
    "reason": "Field 'premium_amount' returned null — the source document does not contain this information. Retry is futile; escalate to human review."
  [exit code: 1]
  ```
  There was one `POST /v1/messages` line, so one API call, and no value was fabricated. Screenshot:
  `01-policy-pipeline/screenshots/perturbation-missing-premium-escalation.png`. The offline suite
  pins the same contract: `test_ac_01_04_missing_source_halts_immediately PASSED`
  (`perturbations/s1-retry-tests.txt`), which asserts `client.call_count == 1  # no further API call`.
- **How this differs from the unperturbed run:** the original document
  (`perturbations/s1-extract-original.txt`) also took one call but returned
  `"kind": "extraction"`, `"premium_amount": 1847.62`, `"retry_count": 0`, exit code 0. The only
  thing that changed was whether the source contained the fact. The system answered "the document is
  silent" instead of "I'll guess". For contrast, in the full pipeline run a *recoverable* failure
  behaves differently: POL-2025-010 logged `validation_failed` (category `consistency`), was retried
  with the error appended, and passed on the second extraction attempt (`pipeline-run.txt` lines
  29–31). That's two extraction calls for a fixable error versus one call for an unfixable one.

---

### System 2 — schema-enforced two-pass extraction

- **Change I made (file + what I changed):** I copied `fixtures/documents/income_sum_mismatch.txt`
  to `perturbations/inputs/income_sum_corrected.txt` and changed only the stated total,
  `TOTAL MONTHLY EARNINGS 10,892.17` → `9,642.17`. The new value is the true sum of the five line
  items, 5,416.67 + 2,140.00 + 1,250.00 + 385.50 + 450.00 (see `income_sum_corrected.diff`). This is
  the reverse of the suggested starter: instead of breaking a clean total, I repaired the broken
  one, to test whether the validator responds to the arithmetic rather than to something else about
  this document.
- **Command I ran (live API, new recording):**
  `mortgage-extract ../../../capstone-submission/perturbations/inputs/income_sum_corrected.txt --mode record --model claude-haiku-4-5-20251001 -v`
- **What I predicted:** the classifier still returns `type=income_verification`, the line items
  extract identically, and `stated_monthly_total` becomes 9642.17. The validator then reports
  `consistent: true` with no discrepancies and exit code 0. If it were still flagged, the check
  would be keyed to something other than the sum.
- **What actually happened (paste the key output line):** from `perturbations/s2-corrected-total-record.txt`:
  ```
  mortgage_extractor.pipeline: classify: model=claude-haiku-4-5-20251001 in=1612 out=95 type=income_verification
      "stated_monthly_total": 9642.17
    "validation": { "consistent": true, "discrepancies": [] }
  [exit code: 0]
  ```
  There was also an unpredicted result: the live model did **not** match the recorded fixture
  outside the income block. The recorded replay of this document returns `"property": null` and
  `"loan": null` (`02-mortgage-extraction/discrepancy-run.txt`). The live run instead filled the
  required objects with placeholders: `"address": "<UNKNOWN>"`, `"property_type": "other"`, and
  `"amount": 0.0` for the loan. The validator still passed it.
- **How this differs from the unperturbed run:** the unperturbed `income_sum_mismatch.txt` run
  (`02-mortgage-extraction/discrepancy-run.txt`, replay) reports `"consistent": false`,
  `"calculated": 9642.17, "stated": 10892.17, "delta": -1250.0` and exits 1. A one-number edit to
  the stated total flipped the verdict, so the validator is driven by the arithmetic. For a second
  contrast, the clean `appraisal_informal_sqft.txt` run (`extract-run.txt`) has no income totals to
  reconcile and reports `"consistent": true, "discrepancies": []`. The drift is the bigger lesson.
  `loan.amount: 0.0` is a fabricated zero that neither JSON-schema enforcement nor the sum check can
  catch, and only comparing a live run against the recording exposed it.

---

### System 3 — multi-source synthesis

- **Change I made (file + what I changed):** configuration only. I added `--simulate-timeout`, which
  makes the `logistics` reader fail mid-run. I made no data edits.
- **Command I ran:** `supply-chain-investigate meridian --offline` (control) and
  `supply-chain-investigate meridian --offline --simulate-timeout` (perturbed). I diffed the two
  briefings into `perturbations/s3-timeout-diff.txt`.
- **What I predicted:** the run still exits 0. Logistics-only metrics (`late_shipment_count`) move to
  **Incomplete** with a timeout reason, and the briefing names the dead source. The on-time-delivery
  conflict should disappear, because one side of it came from logistics.
- **What actually happened (paste the key output line):** from `03-supply-chain/timeout-run.txt`
  (exit code 0):
  ```
  > Sources unavailable: logistics unavailable (timeout)
  ## Well-Established
  ### on_time_delivery_rate  _[single source only]_
      - 95.0 percent — supplier_audit (as of 2026-04-10)
  ## Contested
  _none_
  ## Incomplete
  ### late_shipment_count  _[missing source: timeout reading logistics]_
  - missing source: timeout reading logistics
  ```
  Screenshot: `03-supply-chain/screenshots/timeout-run.png`.
- **How this differs from the unperturbed run:** in `03-supply-chain/briefing.md`,
  `on_time_delivery_rate` is **Contested** and ⚠️ ESCALATE (`95.0 percent — supplier_audit (as of
  2026-04-10)` vs `78.0 percent — logistics (as of 2026-04-05)`), `late_shipment_count` reports
  `11.0 shipments — logistics`, and `average_lead_time_days` is "corroborated across 2 sources".
  With logistics down, the run completes and correctly marks `late_shipment_count` Incomplete. The
  catch is that `on_time_delivery_rate` silently moves to Well-Established as `single source only`
  at the optimistic 95%, and the escalation disappears. The only remaining trace of the 78% is the
  top-line "Sources unavailable" banner. That's graceful degradation working as designed, but a
  reader who skims section headings would see a healthier supplier than the full-data run shows.
