
import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  HiOutlineArrowLeft,
  HiOutlineArrowPath,
  HiOutlineClipboardDocumentCheck,
  HiOutlineExclamationTriangle,
  HiOutlineFire,
  HiOutlineUserGroup,
} from 'react-icons/hi2';
import {
  getTaskAssignments,
  downloadTaskAssignmentPdf,
  runAnalysisExisting,
} from '../services/api';

const PRIORITIES = ['Critical', 'High', 'Medium', 'Low'];

const priorityStyles = {
  Critical: 'text-red-600 bg-red-500/10 border-red-500/30',
  High: 'text-orange-600 bg-orange-500/10 border-orange-500/30',
  Medium: 'text-yellow-600 bg-yellow-500/10 border-yellow-500/30',
  Low: 'text-green-600 bg-green-500/10 border-green-500/30',
};

export default function TaskAssessment({ data, onBack, onAnalysisUpdate }) {
  const [tasks, setTasks] = useState([]);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [priorityFilter, setPriorityFilter] = useState('All');
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState('');
  const [rerunning, setRerunning] = useState(false);
  const [rerunError, setRerunError] = useState('');

  const tenantId = data?.tenant_id;
  const auditRunId = data?.audit_run_id;
  const missingRunInfo = !tenantId || !auditRunId;

  useEffect(() => {
    if (missingRunInfo) {
      return;
    }

    let active = true;

    const loadTasks = async () => {
      setLoading(true);
      setError('');

      try {
        const result = await getTaskAssignments(
          tenantId,
          auditRunId
        );

        if (active) {
          setTasks(result.tasks || []);
          setStatus(result.status || '');
          setPriorityFilter('All');
        }
      } catch (err) {
        if (active) {
          setError(err.message || 'Unable to load tasks.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadTasks();

    return () => {
      active = false;
    };
  }, [tenantId, auditRunId, reloadKey, missingRunInfo]);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setPdfError('');

    try {
      const blob = await downloadTaskAssignmentPdf(
        tenantId,
        auditRunId
      );

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = `FinComply_TaskAssignment_${auditRunId}.pdf`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError(
        err.message || 'Unable to download Task Assignment PDF.'
      );
    } finally {
      setDownloadingPdf(false);
    }
  };

  // Re-analyses the tenant so an audit run created before Task Assessment
  // existed gets its tasks. The new run replaces the current analysis.
  const handleRerun = useCallback(async () => {
    setRerunning(true);
    setRerunError('');

    try {
      const result = await runAnalysisExisting(tenantId);
      onAnalysisUpdate?.(result);
    } catch (err) {
      setRerunError(err.message || 'Unable to re-run the analysis.');
    } finally {
      setRerunning(false);
    }
  }, [tenantId, onAnalysisUpdate]);

  const shownError = missingRunInfo
    ? 'Tenant or audit run information is missing.'
    : error;
  const shownLoading = !missingRunInfo && loading;

  const countFor = (priority) =>
    tasks.filter((task) => task.priority === priority).length;

  const teamCount = new Set(
    tasks.map((task) => task.responsible_team)
  ).size;

  const visibleTasks =
    priorityFilter === 'All'
      ? tasks
      : tasks.filter((task) => task.priority === priorityFilter);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-base"
    >
      <nav className="sticky top-0 z-40 bg-surface/90 backdrop-blur-md border-b border-subtle px-6 py-4">
        <div className="container-center flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 rounded-md text-secondary hover:text-primary hover:bg-elevated"
              aria-label="Back to dashboard"
            >
              <HiOutlineArrowLeft className="text-xl" />
            </button>

            <div>
              <h1 className="text-xl font-bold text-primary">
                Task Assessment
              </h1>
              <p className="text-sm text-secondary">
                Fin-Comply Remediation Assignments
              </p>
            </div>
          </div>

          <div className="hidden sm:block text-right text-sm text-secondary">
            <p>Tenant: {tenantId}</p>
            <p className="text-xs text-muted">Audit run: {auditRunId}</p>
          </div>
        </div>
      </nav>

      <main className="container-center py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-primary">
            Compliance Task Assignments
          </h2>
          <p className="mt-2 text-secondary">
            Actionable remediation tasks generated from the confirmed
            violations of this audit run, each assigned to a responsible team.
          </p>

          <div className="mt-5 flex flex-col items-start gap-3">
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf || shownLoading || !!shownError}
              className="px-5 py-3 rounded-lg font-semibold text-white btn-gradient shadow-glow hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloadingPdf
                ? 'Generating PDF...'
                : 'Download Task Assignment Report'}
            </button>

            {pdfError && (
              <p role="alert" className="text-sm text-red-600">
                {pdfError}
              </p>
            )}
          </div>
        </div>

        {shownLoading ? (
          <div className="py-20 text-center text-secondary">
            Loading task assignments...
          </div>
        ) : shownError ? (
          <div
            role="alert"
            className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-600"
          >
            <p>{shownError}</p>
            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-500/40 text-sm font-semibold hover:bg-red-500/10"
            >
              <HiOutlineArrowPath /> Try again
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {[
                {
                  label: 'Total Tasks',
                  value: tasks.length,
                  icon: HiOutlineClipboardDocumentCheck,
                },
                {
                  label: 'Critical Priority',
                  value: countFor('Critical'),
                  icon: HiOutlineFire,
                },
                {
                  label: 'High Priority',
                  value: countFor('High'),
                  icon: HiOutlineExclamationTriangle,
                },
                {
                  label: 'Teams Involved',
                  value: teamCount,
                  icon: HiOutlineUserGroup,
                },
              ].map(({ label, value, icon: Icon }) => (
                <div
                  key={label}
                  className="bg-surface border border-subtle rounded-xl p-5"
                >
                  <Icon className="text-2xl text-brand-primary mb-3" />
                  <p className="text-sm text-secondary">
                    {label}
                  </p>
                  <p className="text-3xl font-bold text-primary mt-1">
                    {value}
                  </p>
                </div>
              ))}
            </div>

            {tasks.length === 0 ? (
              <div className="bg-surface border border-subtle rounded-xl p-10 text-center">
                <HiOutlineClipboardDocumentCheck className="text-4xl text-secondary mx-auto mb-4" />
                {status === 'not_generated' ? (
                  <>
                    <h3 className="text-lg font-semibold text-primary">
                      Tasks not generated for this audit run
                    </h3>
                    <p className="text-secondary mt-2">
                      This audit run was created before Task Assessment was
                      available. Re-run the analysis to generate its tasks.
                    </p>
                    <button
                      type="button"
                      onClick={handleRerun}
                      disabled={rerunning}
                      className="mt-5 inline-flex items-center gap-2 px-5 py-3 rounded-lg font-semibold text-white btn-gradient shadow-glow hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <HiOutlineArrowPath className={rerunning ? 'animate-spin' : ''} />
                      {rerunning ? 'Re-running analysis...' : 'Re-run analysis'}
                    </button>
                    {rerunError && (
                      <p role="alert" className="mt-3 text-sm text-red-600">
                        {rerunError}
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    <h3 className="text-lg font-semibold text-primary">
                      No remediation tasks
                    </h3>
                    <p className="text-secondary mt-2">
                      No confirmed violations were found in this audit run,
                      so there is nothing to assign.
                    </p>
                  </>
                )}
              </div>
            ) : (
              <>
                <div
                  className="flex flex-wrap gap-2 mb-6"
                  role="group"
                  aria-label="Filter tasks by priority"
                >
                  {['All', ...PRIORITIES].map((priority) => {
                    const count =
                      priority === 'All' ? tasks.length : countFor(priority);
                    const selected = priorityFilter === priority;

                    return (
                      <button
                        key={priority}
                        type="button"
                        onClick={() => setPriorityFilter(priority)}
                        disabled={count === 0}
                        aria-pressed={selected}
                        className={`px-4 py-2 rounded-full text-sm font-semibold border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                          selected
                            ? 'bg-brand-primary text-white border-transparent'
                            : 'bg-surface text-secondary border-subtle hover:text-primary'
                        }`}
                      >
                        {priority} ({count})
                      </button>
                    );
                  })}
                </div>

                <div className="space-y-5">
                  {visibleTasks.map((task) => (
                    <div
                      key={`${task.rule_id}-${task.signal_id}`}
                      className="bg-surface border border-subtle rounded-xl p-6"
                    >
                      <div className="flex flex-wrap justify-between gap-3 mb-4">
                        <div>
                          <p className="text-xs font-semibold text-brand-primary mb-2">
                            {task.rule_id}
                            {task.rule_name ? ` · ${task.rule_name}` : ''}
                            {task.signal_id !== 'GENERAL'
                              ? ` · Signal ${task.signal_id}`
                              : ''}
                          </p>

                          <h3 className="text-lg font-bold text-primary">
                            {task.task_title}
                          </h3>
                        </div>

                        <span
                          className={`self-start px-3 py-1 rounded-full text-xs font-semibold border ${
                            priorityStyles[task.priority] ||
                            priorityStyles.Medium
                          }`}
                        >
                          {task.priority}
                        </span>
                      </div>

                      <p className="text-sm text-secondary mb-5">
                        {task.task_description}
                      </p>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                        <div>
                          <p className="text-xs text-muted mb-1">
                            Responsible Team
                          </p>
                          <p className="font-semibold text-primary">
                            {task.responsible_team}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs text-muted mb-1">
                            Affected Records
                          </p>
                          <p className="font-semibold text-primary">
                            {task.affected_records_count}
                          </p>
                        </div>
                      </div>

                      <div className="border-t border-subtle pt-4">
                        <h4 className="font-semibold text-primary mb-3">
                          Recommended Remediation Steps
                        </h4>

                        <ol className="list-decimal pl-5 space-y-2 text-sm text-secondary">
                          {(task.remediation_steps || []).map(
                            (step, index) => (
                              <li key={index}>
                                {typeof step === 'string'
                                  ? step
                                  : JSON.stringify(step)}
                              </li>
                            )
                          )}
                        </ol>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </motion.div>
  );
}
