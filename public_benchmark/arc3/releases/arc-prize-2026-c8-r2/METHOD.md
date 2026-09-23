# Method

## High-level approach

The submitted candidate uses the public Tufa/Duck ARC-AGI-3 harness and keeps its prompt/tool-use/game-loop behavior intact while changing the inference-serving stack and operational hardening around it.

The competition notebook itself states that the main changes are serving/performance oriented rather than a replacement of the Duck solver policy.

Core elements:

1. **Duck/Tufa interactive ARC harness**
   - Competition games are played through the public ARC runtime.
   - The agent receives observations, calls tools/actions, and continues until the game terminates or the configured budget is exhausted.

2. **Pinned Flash-Next model serving**
   - Model: `RadixArk/Qwen3.8-Flash-Next-NVFP4`
   - Pinned model revision:
     `7b719225242aacd3dbd3f9407468c2ee9a9d2594`

3. **vLLM serving**
   - Audited vLLM version:
     `0.1.dev20073+g8e685d198`
   - NVFP4 serving
   - BF16 compute
   - async scheduling
   - chunked prefill
   - native NEXTN/MTP speculative decoding
   - bounded batched-token and sequence settings
   - CUDA graph use
   - prefix caching disabled
   - request/access logs disabled in the competition path

4. **Runtime/watchdog hardening**
   - owned-server watchdog
   - restart only after repeated failed health checks
   - old process/port cleanup verification
   - bounded restart count
   - teardown verification and preservation of required artifacts

5. **Competition execution**
   - 25 games
   - concurrency: 8
   - per-game runtime budget: 7,200 s
   - analyzer timeout: 900 s
   - internet disabled
   - output written under Kaggle working directory

## Truth boundary

The method above is the submitted C8-R2 competition candidate. Public-development diagnostics and later experimental DEUS branches are not retroactively claimed as part of submission ref `56474082`.

Likewise, source-assisted/public-development results elsewhere in the repository do not substitute for Kaggle hidden-test scoring.
