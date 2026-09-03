const DATA_CLASSES = new Set(['public', 'internal', 'private']);

export function validateTask(task) {
  if (!task?.id) throw new Error('task.id is required');
  if (!task?.capability) throw new Error('task.capability is required');
  const dataClass = task.dataClass ?? 'public';
  if (!DATA_CLASSES.has(dataClass)) throw new Error('task.dataClass must be public, internal, or private');
  if (task.deadlineAt && Number.isNaN(Date.parse(task.deadlineAt))) throw new Error('task.deadlineAt must be an ISO date');
  if (task.estimatedCostUsd != null && Number(task.estimatedCostUsd) < 0) throw new Error('task.estimatedCostUsd must be >= 0');
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
  const allowedDataClasses = provider.authorization?.allowedDataClasses ?? ['public'];
  const dataClass = task.dataClass ?? 'public';
  if (!allowedDataClasses.includes(dataClass)) reasons.push('data-class-outside-grant');
  if (dataClass === 'private') {
    const sameLocation = task.dataLocation && provider.dataLocations?.includes(task.dataLocation);
    const explicitEgress = task.allowPrivateEgress === true && provider.dataPolicy?.privateDataAllowed === true;
    if (!sameLocation && !explicitEgress) reasons.push('private-data-egress-not-authorized');
  }
  if (dataClass === 'internal' && provider.dataPolicy?.internalDataAllowed === false) reasons.push('internal-data-not-authorized');
  if (task.requiresNoRetention === true && provider.dataPolicy?.retention !== 'none') reasons.push('retention-policy-mismatch');
  if (task.sideEffect === true && provider.authorization?.allowSideEffects !== true) reasons.push('side-effects-outside-grant');
  if (task.deadlineAt && Date.parse(task.deadlineAt) <= now) reasons.push('task-deadline-expired');
  return { ok: reasons.length === 0, reasons };
}
