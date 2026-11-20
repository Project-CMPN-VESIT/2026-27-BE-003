import json
import logging
from collections import defaultdict
from typing import Any, Optional

import psycopg


# Template used when a confirmed violation fired no actionable signal, so every
# violated rule always produces at least one task.
GENERAL_SIGNAL_ID = "GENERAL"

# Task-assessment status of an audit run, returned to the frontend.
STATUS_GENERATED = "generated"          # tasks exist for this run
STATUS_NO_VIOLATIONS = "no_violations"  # run is clean, nothing to assign
STATUS_NOT_GENERATED = "not_generated"  # run predates the task module


class TaskAssessmentUnavailable(Exception):
    """Task Assessment tables are missing (migrations not applied yet)."""


def build_task_evidence(
    raw_violations: list[dict[str, Any]],
    actionable_keys: Optional[set[tuple[str, str]]] = None,
) -> list[dict[str, Any]]:
    """
    Aggregate confirmed violation evidence by rule and signal.

    This function does not evaluate compliance rules.
    It only processes outcomes already classified as VIOLATION.

    actionable_keys is the set of (rule_id, signal_id) pairs that have an
    active task template. When given, context-only signals are skipped and a
    violation that fired no actionable signal is attributed to the rule's
    GENERAL template. When None, every fired signal is kept.
    """

    grouped = defaultdict(set)

    for violation in raw_violations:
        if violation.get("outcome") != "VIOLATION":
            continue

        rule_id = violation.get("rule_id")
        record_id = violation.get("record_id")
        signals = violation.get("signals_fired") or []

        if not rule_id or not isinstance(signals, list):
            continue

        targets = [
            (rule_id, signal_id)
            for signal_id in signals
            if signal_id
            and (actionable_keys is None or (rule_id, signal_id) in actionable_keys)
        ]
        if (
            not targets
            and actionable_keys is not None
            and (rule_id, GENERAL_SIGNAL_ID) in actionable_keys
        ):
            targets = [(rule_id, GENERAL_SIGNAL_ID)]

        for key in targets:
            # Distinct affected records for each rule/signal.
            # A missing record identifier must not become a
            # fabricated affected-record count.
            if record_id and str(record_id) != "unknown":
                grouped[key].add(str(record_id))
            else:
                grouped.setdefault(key, set())

    return [
        {
            "rule_id": rule_id,
            "signal_id": signal_id,
            "affected_records_count": len(record_ids),
        }
        for (rule_id, signal_id), record_ids in sorted(grouped.items())
    ]


def _active_template_keys(cur) -> set[tuple[str, str]]:
    """
    Active templates that describe the rule definitions in this database.

    A signal template only counts when the rule still has that signal_id
    with the same field it was written for. If a database holds a different
    rule definition, the violation falls back to the GENERAL template rather
    than showing a task for the wrong condition.
    """
    cur.execute(
        """
        SELECT t.rule_id, t.signal_id
        FROM task_templates AS t
        JOIN rules AS r
          ON r.rule_id = t.rule_id
        WHERE t.is_active = TRUE
          AND (
                t.signal_id = %s
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(r.evidence_signals::jsonb) AS s
                    WHERE s->>'signal_id' = t.signal_id
                      AND (t.signal_field IS NULL OR s->>'field' = t.signal_field)
                )
          )
        """,
        (GENERAL_SIGNAL_ID,),
    )
    keys = set()
    for row in cur.fetchall():
        if isinstance(row, dict):
            keys.add((row["rule_id"], row["signal_id"]))
        else:
            keys.add((row[0], row[1]))
    return keys


def save_task_evidence(
    conn,
    tenant_id: str,
    audit_run_id: str,
    raw_violations: list[dict[str, Any]],
) -> int:
    """
    Store task evidence for one tenant and audit run.

    Only signals with an active task template are saved.

    Must be called within the transaction that saves the audit run.
    The caller owns commit/rollback.
    """

    if not tenant_id or not audit_run_id:
        raise ValueError("tenant_id and audit_run_id are required")

    with conn.cursor() as cur:
        # Verify audit run belongs to the requested tenant.
        cur.execute(
            """
            SELECT 1
            FROM audit_runs
            WHERE audit_run_id = %s
              AND tenant_id = %s
            """,
            (audit_run_id, tenant_id),
        )

        if cur.fetchone() is None:
            raise ValueError(
                "Audit run does not exist for the specified tenant"
            )

        evidence = build_task_evidence(
            raw_violations, _active_template_keys(cur)
        )

        # Clear previous evidence for this specific run so that
        # reprocessing is idempotent.
        cur.execute(
            """
            DELETE FROM task_evidence
            WHERE tenant_id = %s
              AND audit_run_id = %s
            """,
            (tenant_id, audit_run_id),
        )

        inserted = 0

        for item in evidence:
            cur.execute(
                """
                INSERT INTO task_evidence (
                    tenant_id,
                    audit_run_id,
                    rule_id,
                    signal_id,
                    affected_records_count
                )
                SELECT
                    %s, %s, t.rule_id, t.signal_id, %s
                FROM task_templates AS t
                WHERE t.rule_id = %s
                  AND t.signal_id = %s
                  AND t.is_active = TRUE
                ON CONFLICT (
                    tenant_id,
                    audit_run_id,
                    rule_id,
                    signal_id
                )
                DO UPDATE SET
                    affected_records_count =
                        EXCLUDED.affected_records_count
                RETURNING id
                """,
                (
                    tenant_id,
                    audit_run_id,
                    item["affected_records_count"],
                    item["rule_id"],
                    item["signal_id"],
                ),
            )

            if cur.fetchone() is not None:
                inserted += 1

    return inserted


def record_task_evidence(
    conn,
    tenant_id: str,
    audit_run_id: str,
    raw_violations: list[dict[str, Any]],
) -> Optional[int]:
    """
    Save task evidence inside a savepoint of the caller's transaction.

    A failure here (for example, task tables not migrated yet) is logged and
    rolled back to the savepoint only, so it can never discard the compliance
    result saved in the same transaction. Returns the number of saved entries,
    or None if saving failed.
    """

    try:
        with conn.transaction():
            count = save_task_evidence(
                conn=conn,
                tenant_id=tenant_id,
                audit_run_id=audit_run_id,
                raw_violations=raw_violations,
            )
        logging.info(
            "Task Assessment: saved %s task evidence entries "
            "for tenant=%s audit_run=%s",
            count,
            tenant_id,
            audit_run_id,
        )
        return count
    except Exception:
        logging.exception(
            "Task Assessment: could not save task evidence for "
            "tenant=%s audit_run=%s; the compliance result is unaffected",
            tenant_id,
            audit_run_id,
        )
        return None


def get_task_assignments(
    conn,
    tenant_id: str,
    audit_run_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve assignments for an exact tenant and audit run.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                t.rule_id,
                r.rule_name,
                t.signal_id,
                t.task_title,
                t.task_description,
                t.responsible_team,
                t.priority,
                t.remediation_steps,
                e.affected_records_count,
                e.audit_run_id,
                e.tenant_id
            FROM task_evidence AS e
            JOIN task_templates AS t
              ON t.rule_id = e.rule_id
             AND t.signal_id = e.signal_id
            JOIN audit_runs AS ar
              ON ar.audit_run_id = e.audit_run_id
             AND ar.tenant_id = e.tenant_id
            LEFT JOIN rules AS r
              ON r.rule_id = t.rule_id
            WHERE e.tenant_id = %s
              AND e.audit_run_id = %s
              AND t.is_active = TRUE
            ORDER BY
                CASE t.priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END,
                t.rule_id,
                CASE WHEN t.signal_id = %s THEN 1 ELSE 0 END,
                t.signal_id
            """,
            (tenant_id, audit_run_id, GENERAL_SIGNAL_ID),
        )

        return cur.fetchall()


def _run_has_violations(conn, tenant_id: str, audit_run_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT result_json
            FROM evaluation_results
            WHERE tenant_id = %s
              AND audit_run_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (tenant_id, audit_run_id),
        )
        row = cur.fetchone()

    if row is None:
        return False

    payload = row["result_json"] if isinstance(row, dict) else row[0]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return False
    if not isinstance(payload, dict):
        return False

    try:
        return int(payload.get("total_violation_occurrences") or 0) > 0
    except (TypeError, ValueError):
        return bool(payload.get("violations"))


def get_task_assessment(
    conn,
    tenant_id: str,
    audit_run_id: str,
) -> dict[str, Any]:
    """
    Return the tasks of one audit run together with its task status.

    Because every confirmed violation produces at least one task (GENERAL
    fallback), a run with violations but no tasks was created before the task
    module existed; it needs to be re-analysed to get tasks.
    """

    try:
        tasks = get_task_assignments(conn, tenant_id, audit_run_id)
    except psycopg.errors.UndefinedTable as exc:
        raise TaskAssessmentUnavailable(
            "Task Assessment is not initialised. Restart the backend so "
            "pending database migrations are applied."
        ) from exc

    if tasks:
        status = STATUS_GENERATED
    elif _run_has_violations(conn, tenant_id, audit_run_id):
        status = STATUS_NOT_GENERATED
    else:
        status = STATUS_NO_VIOLATIONS

    return {
        "tenant_id": tenant_id,
        "audit_run_id": audit_run_id,
        "status": status,
        "total_tasks": len(tasks),
        "tasks": tasks,
    }
