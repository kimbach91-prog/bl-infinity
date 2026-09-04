# Authorized Relay Device Enrollment

A device may participate only after explicit owner/admin authorization.

Required record:
- relay device ID
- authorization reference
- allowed AI providers
- allowed data classes
- credential method
- expiry and revocation path
- local log/storage policy
- network egress policy

The relay must stop when authorization expires or is revoked. Publicly reachable, abandoned, unknown, or third-party devices are not eligible merely because they are accessible or idle.
