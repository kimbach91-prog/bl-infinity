export function normalizeCarbonSignal(input) {
  if (!input || typeof input !== 'object') throw new Error('signal object required');
  const intensity = Number(input.carbonIntensity);
  const min = Number(input.minIntensity ?? 0);
  const max = Number(input.maxIntensity ?? Math.max(intensity, 1));
  if (![intensity, min, max].every(Number.isFinite) || max <= min) throw new Error('invalid carbon signal');
  const norm = Math.max(0, Math.min(1, (intensity - min) / (max - min)));
  return {
    schema: 'deus-carbon-signal/1',
    carbon_intensity_norm: Number(norm.toFixed(6)),
    source: input.source ?? 'UNSPECIFIED',
    observed_at: input.observedAt ?? null,
    external_fetch_performed: false,
  };
}
