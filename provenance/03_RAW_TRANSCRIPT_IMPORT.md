# Exact Raw Transcript Import — required before public priority-grade v1.0

The current runtime can build from the conversation context but does **not expose a one-click byte-for-byte ChatGPT UI transcript export API** to this build process.

Therefore Origin Build v0.1 includes a structured reconstruction rather than falsely claiming exact raw-log fidelity.

For a priority-grade public release:

1. Export/copy the exact conversation transcript.
2. Save unchanged as `provenance/raw/bl-infinity-origin-chat-2026-08-28.md` or `.json`.
3. Do not normalize spelling, punctuation or timestamps in the raw copy.
4. Run:

```bash
sha256sum provenance/raw/bl-infinity-origin-chat-2026-08-28.md
```

5. Commit the hash to `provenance/hash-manifest.json`.
6. Create a signed Git tag/release.
7. Preserve a public or sealed archival copy depending on privacy needs.

The curated public log may remove unrelated/private content, but its entries should point to hashes/offsets in the sealed raw archive when feasible.
