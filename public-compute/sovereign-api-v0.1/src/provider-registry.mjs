export const PROVIDERS = Object.freeze({
  openai: Object.freeze({
    provider_id: 'openai',
    capability_ref: 'cap:provider:openai:runtime',
    api_family: 'responses',
    model_endpoint: 'POST /responses',
    credential_ref: 'secret://OPENAI_API_KEY',
    credential_state: 'BOUND_IN_CANON_NOT_RUNTIME_VERIFIED',
    target_state: 'PLATFORM_TARGET_RESOLVED',
    provider_canary: false,
    billing: {
      mode: 'METERED_OR_CREDIT',
      free_inference_guaranteed: false,
      chatgpt_subscription_includes_api_usage: false
    },
    data_classes: ['S0', 'S1'],
    identity_root: false,
    authority_root: false
  })
});

export function publicProviderRegistry() {
  return Object.values(PROVIDERS).map((provider) => ({
    provider_id: provider.provider_id,
    capability_ref: provider.capability_ref,
    api_family: provider.api_family,
    model_endpoint: provider.model_endpoint,
    credential_state: provider.credential_state,
    target_state: provider.target_state,
    provider_canary: provider.provider_canary,
    billing: provider.billing,
    data_classes: provider.data_classes,
    identity_root: provider.identity_root,
    authority_root: provider.authority_root
  }));
}

export function planTransportRoute({
  requires_inference = false,
  preferred_provider = null,
  data_class = 'S0',
  operation = 'PACKET_EXCHANGE'
} = {}) {
  if (['S2', 'S3', 'S4'].includes(data_class)) {
    return {
      state: 'HOLD',
      code: 'SEALED_ROUTE_REQUIRED',
      operation,
      data_class,
      model_usage: false
    };
  }

  if (!requires_inference) {
    return {
      state: 'READY',
      code: 'ZERO_MODEL_FAST_PATH',
      operation,
      data_class,
      model_usage: false,
      provider_inference_cost: 0,
      transports: ['HTTPS', 'WEBHOOK', 'MCP_OR_EQUIVALENT_AUTHORIZED_BRIDGE'],
      semantics: 'No model call is required for handshake/capability/ref/receipt/event exchange. Hosting/network/provider transport costs, if any, remain external facts.'
    };
  }

  if (preferred_provider && preferred_provider !== 'openai') {
    return {
      state: 'HOLD',
      code: 'PROVIDER_NOT_REGISTERED_IN_V0_1',
      preferred_provider,
      data_class,
      model_usage: false
    };
  }

  const openai = PROVIDERS.openai;
  if (!openai.provider_canary) {
    return {
      state: 'HOLD',
      code: 'OPENAI_ROUTE_NOT_RUNTIME_VERIFIED',
      preferred_provider: 'openai',
      capability_ref: openai.capability_ref,
      credential_state: openai.credential_state,
      data_class,
      model_usage: false,
      free_inference_guaranteed: false,
      next_gate: 'secret-store injection + bounded OpenAI Responses API canary + receipt'
    };
  }

  return {
    state: 'READY',
    code: 'OPENAI_RESPONSES_ROUTE',
    preferred_provider: 'openai',
    capability_ref: openai.capability_ref,
    data_class,
    model_usage: true,
    billing_mode: openai.billing.mode,
    free_inference_guaranteed: false
  };
}
