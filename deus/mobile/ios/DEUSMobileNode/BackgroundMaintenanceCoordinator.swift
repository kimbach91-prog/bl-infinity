import BackgroundTasks
import CryptoKit
import Foundation

enum BackgroundMaintenanceCoordinator {
    static let taskIdentifier = "io.blinfinity.deus.mobile.maintenance"
    static let nodeID = "DEV-MOBILE-IPHONE13_1-OWNER-001"

    private struct BackgroundReceipt: Codable {
        let schema: String
        let nodeID: String
        let timestamp: String
        let modelIdentifier: String
        let osVersion: String
        let processorCount: Int
        let activeProcessorCount: Int
        let physicalMemoryBytes: UInt64
        let thermalState: String
        let lowPowerMode: Bool
        let policy: String
        let outcome: String
        let iterations: Int
        let elapsedSeconds: Double?
        let opsPerSecond: Double?
        let digestHex: String?
        let truthBoundary: String
    }

    static func register() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: taskIdentifier,
            using: nil
        ) { task in
            guard let processingTask = task as? BGProcessingTask else {
                task.setTaskCompleted(success: false)
                return
            }
            handle(processingTask)
        }
    }

    static func schedule() {
        BGTaskScheduler.shared.cancel(taskRequestWithIdentifier: taskIdentifier)

        let request = BGProcessingTaskRequest(identifier: taskIdentifier)
        request.requiresExternalPower = true
        request.requiresNetworkConnectivity = false
        request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60)

        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            // Scheduling is opportunistic and OS-controlled. Failure to schedule is not
            // promoted to a runtime claim; foreground telemetry remains available.
        }
    }

    private static func handle(_ task: BGProcessingTask) {
        schedule()

        let worker = Task.detached(priority: .background) {
            await runMaintenance()
        }

        task.expirationHandler = {
            worker.cancel()
        }

        Task {
            let success = await worker.value
            task.setTaskCompleted(success: success)
        }
    }

    private static func runMaintenance() async -> Bool {
        guard !Task.isCancelled else { return false }

        let process = ProcessInfo.processInfo
        let thermal = thermalText(process.thermalState)
        let lowPower = process.isLowPowerModeEnabled

        let iterations: Int
        let outcome: String

        if lowPower {
            iterations = 0
            outcome = "YIELD_LOW_POWER_MODE"
        } else {
            switch process.thermalState {
            case .critical:
                iterations = 0
                outcome = "YIELD_THERMAL_CRITICAL"
            case .serious:
                iterations = 0
                outcome = "YIELD_THERMAL_SERIOUS"
            case .fair:
                iterations = 1_000
                outcome = "BOUNDED_CANARY_FAIR_THERMAL"
            case .nominal:
                iterations = 2_000
                outcome = "BOUNDED_CANARY_NOMINAL"
            @unknown default:
                iterations = 0
                outcome = "YIELD_THERMAL_UNKNOWN"
            }
        }

        guard !Task.isCancelled else { return false }

        let canary = iterations > 0 ? sha256Canary(iterations: iterations) : nil
        let receipt = BackgroundReceipt(
            schema: "DEUS_MOBILE_BACKGROUND_RECEIPT/v0.2",
            nodeID: nodeID,
            timestamp: ISO8601DateFormatter().string(from: Date()),
            modelIdentifier: hardwareModelIdentifier(),
            osVersion: process.operatingSystemVersionString,
            processorCount: process.processorCount,
            activeProcessorCount: process.activeProcessorCount,
            physicalMemoryBytes: process.physicalMemory,
            thermalState: thermal,
            lowPowerMode: lowPower,
            policy: "CHARGING_ONLY_OS_SCHEDULED_OFFLOAD_FIRST",
            outcome: outcome,
            iterations: iterations,
            elapsedSeconds: canary?.elapsedSeconds,
            opsPerSecond: canary?.opsPerSecond,
            digestHex: canary?.digestHex,
            truthBoundary: "OS-scheduled own-app background processing only; no persistence guarantee, root, jailbreak, kernel control, other-process control, or hidden resource use."
        )

        return write(receipt)
    }

    private static func write(_ receipt: BackgroundReceipt) -> Bool {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
            let data = try encoder.encode(receipt)
            let directory = FileManager.default.urls(
                for: .documentDirectory,
                in: .userDomainMask
            )[0]
            let url = directory.appendingPathComponent(
                "DEUSBackgroundReceipt-\(Int(Date().timeIntervalSince1970)).json"
            )
            try data.write(to: url, options: .atomic)
            return true
        } catch {
            return false
        }
    }

    private static func sha256Canary(
        iterations: Int
    ) -> (elapsedSeconds: Double, opsPerSecond: Double, digestHex: String) {
        var payload = Data("DEUS::IPHONE13,1::BACKGROUND_CANARY".utf8)
        let start = CFAbsoluteTimeGetCurrent()
        var digest = SHA256.hash(data: payload)

        for i in 0..<iterations {
            if Task.isCancelled { break }
            payload = Data(digest)
            var counter = UInt64(i).bigEndian
            withUnsafeBytes(of: &counter) { payload.append(contentsOf: $0) }
            digest = SHA256.hash(data: payload)
        }

        let elapsed = max(CFAbsoluteTimeGetCurrent() - start, 0.000_001)
        let digestHex = digest.map { String(format: "%02x", $0) }.joined()
        return (elapsed, Double(iterations) / elapsed, digestHex)
    }

    private static func thermalText(_ state: ProcessInfo.ThermalState) -> String {
        switch state {
        case .nominal: return "nominal"
        case .fair: return "fair"
        case .serious: return "serious"
        case .critical: return "critical"
        @unknown default: return "unknown"
        }
    }

    private static func hardwareModelIdentifier() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let mirror = Mirror(reflecting: systemInfo.machine)
        return mirror.children.reduce(into: "") { result, element in
            guard let value = element.value as? Int8, value != 0 else { return }
            result.append(Character(UnicodeScalar(UInt8(value))))
        }
    }
}
