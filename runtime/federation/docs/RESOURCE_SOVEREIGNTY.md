# Resource Sovereignty

BL Compute Federation treats compute as a revocable grant, not as an ambient resource.

A provider may enter the routing set only when the grantor, consent reference, exact capabilities, allowed data classes, resource limits, expiry/revocation, transport authentication and data-locality/retention rules are known. A technical path to a machine does not satisfy this rule.

A grant is fail-closed. `revokedAt`, expiry, operator disablement or loss of required credentials removes the provider from the eligible set.

Private data is routed only when it stays at the declared `dataLocation`, or the task explicitly allows private egress and the provider grant/policy allows private data. Tasks can additionally require `retention=none`.

Browser visitors, public CI runners, public Wi-Fi, unaffiliated servers, exposed APIs and third-party free tiers are not federation nodes merely because they are reachable. Volunteer/browser compute would require clear opt-in, visible limits, pause/revoke controls and a narrow capability sandbox before admission.
