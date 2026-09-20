import { TaskExecutor } from "@golem-sdk/task-executor";
import { pinoPrettyLogger } from "@golem-sdk/pino-logger";

const started = Date.now();
const executor = await TaskExecutor.create({
  logger: pinoPrettyLogger({ level: "info" }),
  api: { key: process.env.YAGNA_APPKEY || "try_golem" },
  payment: { network: "hoodi" },
  demand: {
    workload: { imageTag: "golem/node:20-alpine" }
  },
  market: {
    rentHours: 0.05,
    pricing: {
      model: "linear",
      maxStartPrice: 0.5,
      maxCpuPerHourPrice: 1.0,
      maxEnvPerHourPrice: 0.5
    }
  },
  task: {
    maxParallelTasks: 1
  }
});

try {
  const output = await executor.run(async (exe) => {
    const run = await exe.run(`node -e "process.stdout.write(String(329*334+106))"`);
    return {
      result: String(run.stdout || "").trim(),
      provider_name: exe.provider?.name || "UNKNOWN",
      provider_id: exe.provider?.id || "UNKNOWN"
    };
  }, { timeout: 120000, startupTimeout: 120000, maxRetries: 2 });

  const stats = executor.getStats();
  const receipt = {
    schema: "deus-golem-testnet-canary/1",
    canary_id: "CANARY-A",
    expected_result: "109992",
    observed_result: output.result,
    exact_match: output.result === "109992",
    provider_name: output.provider_name,
    provider_id: output.provider_id,
    payment_network: "hoodi",
    token_class: "TESTNET_TGLM",
    real_money_spend_authorized: false,
    canonical_write: false,
    protected_core_exported: false,
    elapsed_ms: Date.now() - started,
    stats,
    truth_boundary: "TESTNET_RESULT_VERIFIED != MAINNET_CAPACITY_OR_ECONOMIC_YIELD"
  };
  console.log("DEUS_GOLEM_RECEIPT=" + JSON.stringify(receipt));
  if (!receipt.exact_match) process.exitCode = 2;
} finally {
  await executor.shutdown();
}
