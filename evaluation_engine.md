# Compliance Evaluation Engine

This document outlines the inner workings of the evaluation engine, specifically focusing on how signals evaluate individual records, how rule scores are generated, and the exact mathematical formula used to calculate risk.

## 1. What are Signals?

**Signals** are granular, condition-based checks or evidence requirements defined within DPDP rules. Instead of returning a simple binary pass/fail for an entire rule, the engine evaluates a sequence of signals for each database row to determine a final score for that row.

Each signal consists of:
*   **Field**: The database column or JSON attribute being evaluated (e.g., `consent_date`, `is_minor`).
*   **Operator**: The logical operation to perform (e.g., `equals`, `is_outdated`, `greater_than`, `not_subset_of`). The engine also supports custom Python native evaluators for complex checks.
*   **Target Value**: The threshold or expected value for comparison.
*   **Weight**: A numerical weight representing the signal's contribution to the rule's overall violation score if the signal fires.

### Signal Evaluation
For each relevant database row, the `evaluate_all_signals` function processes every signal associated with the rule. If the condition of a signal is met (i.e., it "fires"), its **weight** is added to the row's `rule_score`. 

```python
# Row-level Rule Score Calculation
rule_score = sum(signal.weight for signal in rule.signals if signal.fires(row))
```

The resulting `rule_score` is then compared against predefined thresholds:
*   **VIOLATION**: `rule_score >= violation_threshold`
*   **WARNING**: `rule_score >= risk_threshold`
*   **PASS**: `rule_score < risk_threshold`

## 2. Risk Calculation Formula

When records trigger `VIOLATION` outcomes, the engine aggregates these to calculate a dynamic, system-wide **Risk Score (0.0 to 100.0)**. 

The risk calculation occurs in two main phases: calculating the **Contribution** of each violated rule, and then **Normalizing** those contributions.

### A. Per-Rule Risk Contribution

For each violated rule, all violations are first deduplicated by `record_id`. The engine then calculates a `contribution` factor:

$$Contribution = Likelihood \times Impact \times Risk\ Weight$$

**1. Likelihood**
Likelihood represents the prevalence of the violation across the dataset.

$$Likelihood = Prevalence\ Ratio \times Recurrence\ Factor$$
*   **Prevalence Ratio**: $min\left(\frac{Affected\ Rows}{Total\ Opportunity\ Count}, 1.0\right)$
*   **Recurrence Factor**: A bonus applied for repeated violations across multiple rows. $1.0 + min(Step \times (Affected\ Rows - 1), Max\ Bonus)$

**2. Impact**
Impact calculates the severity of the violation using a weighted sum of three factors:

$$Impact = (0.4 \times Severity\ Score) + (0.3 \times Penalty\ Norm) + (0.3 \times Signal\ Strength)$$
*   **Severity Score**: A numeric mapping of the rule's string severity (e.g., HIGH, CRITICAL).
*   **Penalty Norm**: $\frac{Rule\ Penalty\ Exposure}{Max\ Statutory\ Penalty\ (MAX\_PENALTY\_CRORE)}$
*   **Signal Strength**: The maximum `rule_score` observed across all violated rows for this rule.

### B. Dynamic Normalization

After calculating the `contribution` for all violated rules, the engine sums them up into a `raw_score` and normalizes it against the maximum possible score (the sum of `risk_weight` for all *active* and *applicable* rules).

$$Normalized\ Risk\ Score = \min\left(\frac{\sum Contributions}{\sum Active\ Rule\ Weights} \times 100.0, 100.0\right)$$

### C. Severity Floor Policies (Deterministic Overrides)

To align with statutory strictness, the DPDP engine enforces minimum floors on the risk score, overriding the mathematical formula if highly severe violations are detected:

> [!IMPORTANT]
> **Severity Floors applied after Normalization:**
> 1. **CRITICAL Violation**: If any `CRITICAL` violation is detected, the risk score is forced to a minimum of **65.0** (Guarantees at least a `HIGH` risk tier).
> 2. **Multiple HIGH Violations**: If 3 or more `HIGH` severity violations are detected, the risk score is forced to a minimum of **45.0** (Guarantees at least a `MEDIUM` risk tier).
