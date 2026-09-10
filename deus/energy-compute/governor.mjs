export function scoreJob(job, signal, cfg = {}) {
  const maxRisk = cfg.maxRisk ?? 0.35;
  const carbonWeight = cfg.carbonWeight ?? 0.35;
  const priceWeight = cfg.priceWeight ?? 0.30;
  const urgencyWeight = cfg.urgencyWeight ?? 0.20;
  const reliabilityWeight = cfg.reliabilityWeight ?? 0.15;

  const bounded01 = (x) => Math.max(0, Math.min(1, Number(x)));
  const authority = job.authority === true;
  const runtimeVerified = job.runtime_verified === true;
  const risk = bounded01(job.risk_score ?? 1);
  const deadlineFeasible = job.deadline_feasible !== false;

  const cleaner = 1 - bounded01(signal.carbon_intensity_norm ?? 1);
  const cheaper = 1 - bounded01(signal.energy_price_norm ?? 1);
  const urgency = bounded01(job.urgency ?? 0);
  const reliability = bounded01(signal.runtime_reliability ?? 0);

  const utility =
    carbonWeight * cleaner +
    priceWeight * cheaper +
    urgencyWeight * urgency +
    reliabilityWeight * reliability;

  const eligible = authority && runtimeVerified && deadlineFeasible && risk <= maxRisk;

  return {
    schema: 'deus-energy-compute-decision/1',
    job_id: job.job_id,
    eligible,
    utility: Number(utility.toFixed(6)),
    gates: {
      authority,
      runtime_verified: runtimeVerified,
      deadline_feasible: deadlineFeasible,
      risk_ok: risk <= maxRisk,
    },
    action: eligible ? 'CANDIDATE_DISPATCH' : 'HOLD',
    truth_boundary: 'RECOMMENDATION_ONLY_UNLESS_EXECUTION_AUTHORITY_RECEIPT_EXISTS',
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const sampleJob = {
    job_id: 'SAMPLE-001',
    authority: true,
    runtime_verified: true,
    deadline_feasible: true,
    risk_score: 0.1,
    urgency: 0.4,
  };
  const sampleSignal = {
    carbon_intensity_norm: 0.2,
    energy_price_norm: 0.3,
    runtime_reliability: 0.95,
  };
  console.log(JSON.stringify(scoreJob(sampleJob, sampleSignal), null, 2));
}
