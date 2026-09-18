import SwiftUI
import UIKit

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        BackgroundMaintenanceCoordinator.register()
        BackgroundMaintenanceCoordinator.schedule()
        return true
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        BackgroundMaintenanceCoordinator.schedule()
    }
}

@main
struct DEUSMobileNodeApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var model = NodeTelemetryModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .task {
                    model.start()
                    BackgroundMaintenanceCoordinator.schedule()
                }
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var model: NodeTelemetryModel

    var body: some View {
        NavigationStack {
            List {
                Section("Node") {
                    LabeledContent("Node ID", value: model.nodeID)
                    LabeledContent("Model", value: model.snapshot.modelIdentifier)
                    LabeledContent("OS", value: model.snapshot.osVersion)
                    LabeledContent("CPU logical", value: "\(model.snapshot.processorCount)")
                    LabeledContent("CPU active", value: "\(model.snapshot.activeProcessorCount)")
                    LabeledContent(
                        "Physical memory",
                        value: ByteCountFormatter.string(
                            fromByteCount: Int64(model.snapshot.physicalMemoryBytes),
                            countStyle: .memory
                        )
                    )
                }

                Section("Sensitive telemetry") {
                    LabeledContent("Thermal", value: model.snapshot.thermalState)
                    LabeledContent("Low Power Mode", value: model.snapshot.lowPowerMode ? "ON" : "OFF")
                    LabeledContent("Battery", value: model.snapshot.batteryText)
                    LabeledContent(
                        "Scheduler budget",
                        value: String(format: "%.2f%%", model.snapshot.schedulerDutyCyclePercent)
                    )
                }

                Section("Bounded canary") {
                    Button(model.isBenchmarkRunning ? "Running…" : "Run compute canary") {
                        Task { await model.runBenchmarkAndWriteReceipt() }
                    }
                    .disabled(model.isBenchmarkRunning || model.snapshot.schedulerDutyCyclePercent <= 0)

                    if let score = model.lastBenchmarkOpsPerSecond {
                        LabeledContent("SHA-256 ops/s", value: String(format: "%.0f", score))
                    }

                    if let url = model.lastReceiptURL {
                        Text("Receipt: \(url.lastPathComponent)")
                            .font(.footnote)
                            .textSelection(.enabled)
                    }
                }

                Section("Background optimization") {
                    Text("iOS may grant a charging-only BGProcessing window. DEUS uses it for a tiny thermal-aware maintenance canary and receipt, and yields under Low Power Mode or serious/critical thermal pressure.")
                        .font(.footnote)
                    Text("Heavy work remains offload-first. This is not a persistent daemon and does not bypass iOS scheduling.")
                        .font(.footnote)
                }

                Section("Truth boundary") {
                    Text("This app measures only APIs and work visible inside its iOS sandbox. It does not claim root, jailbreak, raw GPU/ANE counters, arbitrary process access, kernel control, or unrestricted hardware control.")
                        .font(.footnote)
                }
            }
            .navigationTitle("DEUS Mobile Node")
            .refreshable { model.sample() }
        }
    }
}
