# BL-HC-01 Local Runtime Service

Local-first reference runtime for Huyền Cơ. It binds `127.0.0.1` by default and has no generic shell, dynamic eval or request-selected arbitrary URL capability.

Required environment for live inference:

- `BL_HC_API_TOKEN`: random local bearer token for `/v1/chat`;
- `BL_HC_MODEL_ENDPOINT`: explicitly authorized OpenAI-compatible chat-completions base endpoint;
- `BL_HC_MODEL_NAME`: configured base model name;
- `BL_HC_MODEL_API_KEY`: optional provider/local-gateway credential, kept in a node secret store rather than Drive;
- `BL_HC_HOME`: extracted portable state root.

Start with `python huyen_co_service.py`. Health is exposed at `GET http://127.0.0.1:8789/health`; status at `/v1/agent/status`; chat at `POST /v1/chat` with the node-local bearer token.

Every task produces a local execution receipt. Model output remains candidate-only until reviewed/promoted under the BL-HC-01 memory and governance contracts.

A live service does not by itself create remote routing authority. DEUS/physical-node activation still requires the secure transport, provider grant and authenticated heartbeat gates defined elsewhere.
