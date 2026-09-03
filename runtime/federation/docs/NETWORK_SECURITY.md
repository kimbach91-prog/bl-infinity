# Network Security

Remote worker URLs are treated as security-sensitive configuration. The reference HTTP adapter requires HTTPS for remote nodes, rejects credentials embedded in URLs, blocks IP literals in loopback/private/link-local/reserved ranges by default, and resolves DNS before dispatch to reject names that currently point at restricted addresses.

Private-network workers are possible only when the provider transport explicitly sets `allowPrivateNetwork=true`. That flag belongs inside the signed provider grant, so changing it invalidates the grant signature.

Application checks are defense in depth, not a substitute for infrastructure egress policy. Production coordinators should also use outbound firewall rules, private service networking where appropriate, DNS controls, least-privilege service identities and no direct access to metadata/admin endpoints from general worker-dispatch paths. DNS can change between validation and connection, so infrastructure-level controls remain necessary against rebinding and routing surprises.

Secrets stay outside manifests. HMAC/bearer/Cloudflare service credentials are referenced by environment-variable name. GCP service-to-service auth can use short-lived identity tokens from the metadata identity endpoint rather than storing long-lived cloud keys.
