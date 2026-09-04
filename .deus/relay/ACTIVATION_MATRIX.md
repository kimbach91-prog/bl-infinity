# DEUS Relay Activation Matrix

| Provider | Relay contract | Current proof | Activation requirement |
|---|---|---|---|
| OpenAI | READY | no provider-side relay proof | authorized API/session credential |
| Anthropic / Claude | READY | prior Drive heartbeat return observed | persistent authorized consumer or API credential |
| Google / Gemini | READY | manual E2E verified | persistent authorized consumer or API credential |
| xAI / Grok | READY as task-contract | manual task capability verified; coordination protocol rejected | use external-critic task contract; API credential for automation |
| GitHub Copilot | READY as issue/PR worker | issue #91 prepared | user-side Copilot agent assignment/entitlement |
| DeepSeek local | READY | not yet instantiated | explicitly authorized local device + isolated runtime |
| DeepSeek cloud | READY for PUBLIC/GREY only | no live credential | authorized API credential + approved data policy |

No row is considered provider-connected merely because the relay contract exists. Provider execution requires independent evidence.