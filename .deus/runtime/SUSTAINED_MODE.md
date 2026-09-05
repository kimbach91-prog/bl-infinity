# Sustained Mode

Sustained mode is the DEUS default for long provider-facing jobs: low bounded concurrency, pacing, checkpoint/resume, delta-first work, provider-directed cooldown, and bounded retries. It optimizes useful work completed per long time horizon rather than requests per second.
