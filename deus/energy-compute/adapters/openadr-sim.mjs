export function simulateOpenAdREvent(event, resource) {
  if (!event || !resource) throw new Error('event and resource required');
  const requested = Number(event.requested_kw ?? 0);
  const available = Number(resource.available_kw ?? 0);
  const maxCurtail = Number(resource.max_curtail_kw ?? available);
  const authority = resource.authority === true;
  const bounded = Math.max(0, Math.min(requested, available, maxCurtail));
  return {
    schema: 'deus-openadr-sim-result/1',
    event_id: String(event.event_id ?? 'UNKNOWN'),
    simulated: true,
    external_dispatch: false,
    authority_present: authority,
    requested_kw: requested,
    simulated_curtail_kw: authority ? bounded : 0,
    decision: authority ? 'SIMULATED_RESPONSE' : 'HOLD_NO_AUTHORITY',
  };
}
