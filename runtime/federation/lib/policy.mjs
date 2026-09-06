const DATA_CLASSES = new Set(['public', 'internal', 'private', 'regulated', 'sealed']);
const VALUE_CLASSES = new Set(['S', 'H0', 'H1', 'H2', 'H3', 'H4', 'PGB', 'PFR']);

export function validateTask(task) {
  if (!task?.id) throw new Error('task.id is required');
  if (!task?.capability) throw new Error('task.capability is required');
  const dataClass = task.dataClass ?? 'public';
  if (!DATA_CLASSES.has(dataClass)) throw new Error('task.dataClass must be public, internal, private, regulated, or sealed');
  if (task.deadlineAt && Number.isNaN(Date.parse(task.deadlineAt))) throw new Error('task.deadlineAt must be an ISO date');
  if (task.estimatedCostUsd != null && Number(task.estimatedCostUsd) < 0) throw new Error('task.estimatedCostUsd must be >= 0');
  if (task.maxEnergyPerUnitJoules != null) {
    const maxEnergy = Number(task.maxEnergyPerUnitJoules);
    if (!Number.isFinite(maxEnergy) || maxEnergy < 0) throw new Error('task.maxEnergyPerUnitJoules must be a non-negative finite number');
  }
  const workloadClass = task.valuePolicy?.workloadClass ?? task.workloadClass ?? null;
  if (workloadClass != null && !VALUE_CLASSES.has(workloadClass)) throw new Error('invalid workload class');
  return true;
}

export function evaluateProvider(provider, task, now = Date.now()) {
  validateTask(task);
  const reasons = [];
  if (provider.status === 'disabled') reasons.push('provider-disabled');
  if (provider.authorization?.revokedAt) reasons.push('authorization-revoked');
  if (provider.authorization?.expiresAt && Date.parse(provider.authorization.expiresAt) <= now) reasons.push('authorization-expired');
  if (!provider.authorization?.consentRef) reasons.push('missing-consent');
  if (!provider.capabilities?.includes(task.capability)) reasons.push('capability-mismatch');
  if ((provider.limits?.maxConcurrency ?? 0) <= (provider.telemetry?.inFlight ?? 0)) reasons.push('concurrency-full');
  if ((task.estimatedCostUsd ?? 0) > (provider.limits?.maxCostPerTaskUsd ?? Infinity)) reasons.push('task-cost-over-provider-limit');
  if ((task.estimatedCostUsd ?? 0) > (provider.authorization?.maxTaskCostUsd ?? Infinity)) reasons.push('task-cost-over-grant-limit');
  if (task.region && provider.regions?.length && !provider.regions.includes(task.region)) reasons.push('region-mismatch');
  if (task.deniedProviders?.includes(provider.id)) reasons.push('provider-denied-by-task');
  for (const tag of task.requiredTags ?? []) if (!provider.tags?.includes(tag)) reasons.push(`missing-tag:${tag}`);

  const energyPerUnitJoules = Number(provider.telemetry?.energyPerUnitJoules);
  const hasEnergyTelemetry = Number.isFinite(energyPerUnitJoules) && energyPerUnitJoules >= 0;
  if (task.requiresEnergyTelemetry === true && !hasEnergyTelemetry) reasons.push('energy-telemetry-required');
  if (task.maxEnergyPerUnitJoules != null) {
    if (!hasEnergyTelemetry) reasons.push('energy-telemetry-required');
    else if (energyPerUnitJoules > Number(task.maxEnergyPerUnitJoules)) reasons.push('provider-energy-over-task-limit');
  }

  const allowedDataClasses = provider.authorization?.allowedDataClasses ?? ['public'];
  const dataClass = task.dataClass ?? 'public';
  if (!allowedDataClasses.includes(dataClass)) reasons.push('data-class-outside-grant');

  const sameLocation = Boolean(task.dataLocation && provider.dataLocations?.includes(task.dataLocation));
  if (dataClass === 'private') {
    const explicitEgress = task.allowPrivateEgress === true && provider.dataPolicy?.privateDataAllowed === true;
    if (!sameLocation && !explicitEgress) reasons.push('private-data-egress-not-authorized');
  }
  if (dataClass === 'regulated' && !sameLocation) reasons.push('regulated-data-location-mismatch');
  if (dataClass === 'sealed' && !sameLocation) reasons.push('sealed-compute-must-go-to-data');
  if (dataClass === 'sealed' && task.allowPrivateEgress === true) reasons.push('sealed-data-egress-forbidden');
  if (dataClass === 'internal' && provider.dataPolicy?.internalDataAllowed === false) reasons.push('internal-data-not-authorized');
  if (task.requiresNoRetention === true && provider.dataPolicy?.retention !== 'none') reasons.push('retention-policy-mismatch');
  if (task.sideEffect === true && provider.authorization?.allowSideEffects !== true) reasons.push('side-effects-outside-grant');
  if (task.deadlineAt && Date.parse(task.deadlineAt) <= now) reasons.push('task-deadline-expired');

  const valuePolicy = task.valuePolicy ?? null;
  if (valuePolicy) {
    const allocation = provider.allocationPolicy ?? {};
    const workloadClass = valuePolicy.workloadClass ?? task.workloadClass;
    const strategicReinvestmentRequested =
      valuePolicy.strategicReinvestmentRequested === true ||
      valuePolicy.commonBenefitRequested === true ||
      workloadClass === 'PGB' ||
      workloadClass === 'PFR';
    const privateFederationReturn =
      valuePolicy.scope === 'private-federation-return' ||
      valuePolicy.scope === 'private-shared-benefit' ||
      workloadClass === 'PGB' ||
      workloadClass === 'PFR';

    const allowStrategicReinvestment = allocation.allowStrategicReinvestment ?? allocation.allowCommonBenefit ?? false;
    const maxStrategicReinvestmentShare = Number(allocation.maxStrategicReinvestmentShare ?? allocation.maxCommonBenefitShare ?? 0);
    const allowPrivateFederationReturn = allocation.allowPrivateFederationReturn ?? allocation.allowPrivateSharedBenefit ?? false;

    if (workloadClass === 'H4' && allocation.allowCommercialWorkloads !== true) reasons.push('commercial-workload-not-opted-in');
    if (strategicReinvestmentRequested && allowStrategicReinvestment !== true) reasons.push('common-benefit-not-opted-in');
    if (privateFederationReturn && allowPrivateFederationReturn !== true) reasons.push('private-shared-benefit-not-opted-in');

    if (strategicReinvestmentRequested) {
      if (!Number.isFinite(maxStrategicReinvestmentShare) || maxStrategicReinvestmentShare <= 0) reasons.push('common-benefit-cap-zero');
      const projectedShare = Number(task.strategicReinvestmentProjectedShare ?? task.commonBenefitProjectedShare);
      if (Number.isFinite(projectedShare) && projectedShare > maxStrategicReinvestmentShare) reasons.push('common-benefit-provider-cap-exceeded');
    }
  }

  return { ok: reasons.length === 0, reasons };
}
