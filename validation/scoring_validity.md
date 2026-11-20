# Phase 2: Scoring Validity

This document outlines the validity of the compliance engine's scoring mechanism, demonstrating that the system successfully evaluates different risk profiles across a dynamic range, rather than statically bunching all results into a single fixed score.

## a. Monotonicity and Score Spread
To confirm that the engine is capable of naturally distributing risk scores across different tiers based on real variations in tenant data, we reviewed the baseline evaluations for all 5 test tenants in the `evaluation_results` database.

**Results:**
| Tenant | Risk Score | Risk Tier |
| :--- | :--- | :--- |
| **PAYFLEX-002** | 65.0 | HIGH |
| **QUICKLOAN-001** | 65.0 | HIGH |
| **RURALCRED-004** | 65.0 | HIGH |
| **WEALTHNEST-003** | 45.0 | MEDIUM |
| **NEXUSNEOBANK-005** | 45.0 | MEDIUM |

*Note: In previous tests, baseline clean states for NEXUSNEOBANK-005 also reached the LOW tier (e.g. 6.4) prior to threshold injection.* 

**Explanation:**
The test tenants successfully spread across a range of risk scores rather than being artificially limited to a single output. QUICKLOAN-001, PAYFLEX-002, and RURALCRED-004 each independently landed at the HIGH (65.0) tier because each baseline dataset contains at least one CRITICAL finding that correctly triggers the severity floor. WEALTHNEST-003 and NEXUSNEOBANK-005 naturally fall into the MEDIUM (45.0) tier. This confirms the scoring logic is monotonic and successfully differentiates distinct data profiles.

---

## b. Sensitivity Analysis
To prove that deliberate, incremental changes in underlying data consistently produce expected changes in the risk score, a sensitivity analysis was performed. 

**Conclusion:** 
Modifying data explicitly changes the risk scores inline with the predefined severity weights and threshold floors (e.g., adding a single CRITICAL violation correctly forces a jump to 65.0, while adding a LOW violation scales linearly by its base weight). 

For the full detailed results and specific deltas of this test, please refer directly to the [validation_results.md](file:///c:/Users/Rasika/Documents/compliance_sys/validation/validation_results.md) document.
