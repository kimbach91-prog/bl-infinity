export function chooseWindow(job, windows, scoreFn) {
  if (!job || !Array.isArray(windows) || windows.length === 0) throw new Error('job/windows required');
  if (typeof scoreFn !== 'function') throw new Error('scoreFn required');
  const candidates = windows.map((w) => ({ window: w, decision: scoreFn(job, w) }));
  const eligible = candidates.filter((x) => x.decision?.eligible === true);
  if (eligible.length === 0) {
    return { schema: 'deus-workload-schedule/1', action: 'HOLD', selected: null, candidates };
  }
  eligible.sort((a, b) => b.decision.utility - a.decision.utility);
  return {
    schema: 'deus-workload-schedule/1',
    action: 'CANDIDATE_DISPATCH',
    selected: eligible[0],
    candidates,
    external_execution_performed: false,
  };
}
