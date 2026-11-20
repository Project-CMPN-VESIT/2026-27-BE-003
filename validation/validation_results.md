# Phase 3b: Sensitivity Analysis

### What was done
We tested the risk scoring algorithm's sensitivity by modifying a single baseline tenant (NEXUSNEOBANK-005). We introduced exactly one change at a time to fresh copies of the CSVs, evaluating how specific threshold boundaries affected the risk score.

### Results
| Test Condition | Risk Score | Delta (from Baseline) | Risk Tier |
| :--- | :--- | :--- | :--- |
| **Baseline** | 6.4 | 0.0 | LOW |
| **Add 1 CRITICAL Violation** | 65.0 | **+58.6** | HIGH |
| **Add 1 LOW Violation** | 7.5 | **+1.1** | LOW |
| **Double Rows** | 6.4 | **0.0** | LOW |
| **3+ HIGH Threshold** | 45.0 | **+38.6** | MEDIUM |

### Explanation
- **Baseline**: The baseline score is 6.4 (LOW tier). 
- **Add 1 CRITICAL Violation**: Introducing a single critical rule failure (DPDP-008: PII unencrypted) successfully forced the score to jump directly to the 65.0 minimum CRITICAL floor.
- **Add 1 LOW Violation**: Adding a low severity rule (DPDP-009: Incomplete DPIA) merely incremented the risk score by its small base weight (+1.1), proving that low violations scale linearly without triggering tier floors.
- **Double Rows**: Duplicating a violating row for an already broken rule (DPDP-001) produced a 0.0 delta, confirming that the engine deduplicates violations at the rule level rather than accumulating penalties per row.
- **3+ HIGH Threshold**: Injecting multiple HIGH rule failures (DPDP-003 and DPDP-010) safely pushed the unique HIGH rule count across the 3+ boundary, successfully triggering the 45.0 MEDIUM floor.
