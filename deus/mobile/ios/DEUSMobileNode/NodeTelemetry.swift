import Foundation
import UIKit
import CryptoKit

struct NodeSnapshot: Codable {
    let timestamp: String
    let modelIdentifier: String
    let osVersion: String
    let processorCount: Int
    let activeProcessorCount: Int
    let physicalMemoryBytes: UInt64
    let thermalState: String
    let lowPowerMode: Bool
    let batteryLevel: Float
    let batteryState: String
    let schedulerDutyCyclePercent: Double

    var batteryText: String {
        if batteryLevel < 0 { return "unknown / \(batteryState)" }
        return "\(Int(batteryLevel * 100))% / \(batteryState)"
    }
}

struct NodeReceipt: Codable {
    let schema: String
    let nodeID: String
    let snapshot: NodeSnapshot
    let canary: String
    let iterations: Int
    let elapsedSeconds: Double
    let opsPerSecond: Double
    let digestHex: String
    let truthBoundary: String
}

@MainActor
final class NodeTelemetryModel: ObservableObject {
    let nodeID = "DEV-MOBILE-IPHONE13_1-OWNER-001"

    @Published var snapshot: NodeSnapshot
    @Published var isBenchmarkRunning = false
    @Published var lastBenchmarkOpsPerSecond: Double?
    @Published var lastReceiptURL: URL?

    private var timer: Timer?

    init() {
        UIDevice.current.isBatteryMonitoringEnabled = true
        snapshot = Self.captureSnapshot()
    }

    func start() {
        sample()
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.sample() }
        }
    }

    func sample() {
        snapshot = Self.captureSnapshot()
    }

    func runBenchmarkAndWriteReceipt() async {
        guard !isBenchmarkRunning else { return }
        isBenchmarkRunning = true
        defer { isBenchmarkRunning = false }

        sample()
        let budget = snapshot.schedulerDutyCyclePercent
        guard budget > 0 else { return }

        let iterations = Self.iterationsForBudget(budget)
        let result = await Task.detached(priority: .utility) {
            Self.sha256Canary(iterations: iterations)
        }.value

        sample()
        lastBenchmarkOpsPerSecond = result.opsPerSecond

        let receipt = NodeReceipt(
            schema: "DEUS_MOBILE_NODE_RECEIPT/v0.1",
            nodeID: nodeID,
            snapshot: snapshot,
            canary: "SHA256_BOUNDED_V1",
            iterations: iterations,
            elapsedSeconds: result.elapsedSeconds,
            opsPerSecond: result.opsPerSecond,
            digestHex: result.digestHex,
            truthBoundary: "Own-app sandbox telemetry and bounded own-process benchmark only; no jailbreak/root/raw GPU/process-table claim."
        )

        do {
            let data = try JSONEncoder.pretty.encode(receipt)
            let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let url = dir.appendingPathComponent("DEUSNodeReceipt-\(Int(Date().timeIntervalSince1970)).json")
            try data.write(to: url, options: .atomic)
            lastReceiptURL = url
        } catch {
            lastReceiptURL = nil
        }
    }

    private static func captureSnapshot() -> NodeSnapshot {
        let p = ProcessInfo.processInfo
        let device = UIDevice.current
        return NodeSnapshot(
            timestamp: ISO8601DateFormatter().string(from: Date()),
            modelIdentifier: hardwareModelIdentifier(),
            osVersion: "\(device.systemName) \(device.systemVersion)",
            processorCount: p.processorCount,
            activeProcessorCount: p.activeProcessorCount,
            physicalMemoryBytes: p.physicalMemory,
            thermalState: thermalText(p.thermalState),
            lowPowerMode: p.isLowPowerModeEnabled,
            batteryLevel: device.batteryLevel,
            batteryState: batteryStateText(device.batteryState),
            schedulerDutyCyclePercent: dutyCyclePercent(
                thermal: p.thermalState,
                lowPower: p.isLowPowerModeEnabled,
                batteryLevel: device.batteryLevel,
                batteryState: device.batteryState
            )
        )
    }

    private static func dutyCyclePercent(
        thermal: ProcessInfo.ThermalState,
        lowPower: Bool,
        batteryLevel: Float,
        batteryState: UIDevice.BatteryState
    ) -> Double {
        switch thermal {
        case .critical: return 0.0
        case .serious: return 0.25
        case .fair: return lowPower ? 0.25 : 0.5
        case .nominal:
            if lowPower { return 0.5 }
            if batteryState == .charging || batteryState == .full { return 2.0 }
            if batteryLevel >= 0 && batteryLevel < 0.20 { return 0.25 }
            return 1.0
        @unknown default:
            return 0.25
        }
    }

    private static func iterationsForBudget(_ percent: Double) -> Int {
        switch percent {
        case ..<0.5: return 2_000
        case ..<1.0: return 5_000
        case ..<2.0: return 10_000
        default: return 20_000
        }
    }

    nonisolated private static func sha256Canary(iterations: Int) -> (elapsedSeconds: Double, opsPerSecond: Double, digestHex: String) {
        var payload = Data("DEUS::IPHONE13,1::CANARY".utf8)
        let start = CFAbsoluteTimeGetCurrent()
        var digest = SHA256.hash(data: payload)
        for i in 0..<iterations {
            payload = Data(digest)
            var counter = UInt64(i).bigEndian
            withUnsafeBytes(of: &counter) { payload.append(contentsOf: $0) }
            digest = SHA256.hash(data: payload)
        }
        let elapsed = max(CFAbsoluteTimeGetCurrent() - start, 0.000_001)
        let hex = digest.map { String(format: "%02x", $0) }.joined()
        return (elapsed, Double(iterations) / elapsed, hex)
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

    private static func batteryStateText(_ state: UIDevice.BatteryState) -> String {
        switch state {
        case .unknown: return "unknown"
        case .unplugged: return "unplugged"
        case .charging: return "charging"
        case .full: return "full"
        @unknown default: return "unknown"
        }
    }

    private static func hardwareModelIdentifier() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let mirror = Mirror(reflecting: systemInfo.machine)
        let identifier = mirror.children.reduce(into: "") { result, element in
            guard let value = element.value as? Int8, value != 0 else { return }
            result.append(Character(UnicodeScalar(UInt8(value))))
        }
        return identifier
    }
}

private extension JSONEncoder {
    static var pretty: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        return encoder
    }
}
