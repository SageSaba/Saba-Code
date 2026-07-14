import SwiftUI
#if canImport(AppKit)
import AppKit
#endif
#if canImport(UIKit)
import UIKit
#endif

struct WindowSizeAccessor: View {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    var body: some View {
        if #available(iOS 14.0, macOS 11.0, *) {
            WindowSizeAccessorBridge(initialSize: initialSize, onChange: onChange)
                .frame(width: 0, height: 0)
        } else {
            EmptyView()
        }
    }
}

private struct WindowSizeAccessorBridge: View {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    var body: some View {
        #if canImport(UIKit)
        UIKitWindowSizeAccessor(initialSize: initialSize, onChange: onChange)
        #else
        AppKitWindowSizeAccessor(initialSize: initialSize, onChange: onChange)
        #endif
    }
}

#if canImport(UIKit)
private struct UIKitWindowSizeAccessor: UIViewControllerRepresentable {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    func makeUIViewController(context: Context) -> UIViewController {
        let controller = UIViewController()
        controller.view.isHidden = true
        return controller
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {
        DispatchQueue.main.async {
            guard let window = uiViewController.view.window else { return }

            if !context.coordinator.didSetInitialSize {
                context.coordinator.didSetInitialSize = true
                var frame = window.frame
                frame.size = initialSize
                window.setFrame(frame, display: true)
            }

            let newSize = window.bounds.size
            if newSize != context.coordinator.lastReportedSize {
                context.coordinator.lastReportedSize = newSize
                onChange(newSize)
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator: NSObject {
        var lastReportedSize: CGSize = .zero
        var didSetInitialSize = false
    }
}
#else
private struct AppKitWindowSizeAccessor: NSViewControllerRepresentable {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    func makeNSViewController(context: Context) -> NSViewController {
        let controller = NSViewController()
        controller.view = NSView(frame: .zero)
        controller.view.isHidden = true
        return controller
    }

    func updateNSViewController(_ nsViewController: NSViewController, context: Context) {
        DispatchQueue.main.async {
            guard let window = nsViewController.view.window else { return }

            if !context.coordinator.didSetInitialSize {
                context.coordinator.didSetInitialSize = true
                window.setContentSize(initialSize)
            }

            let newSize = window.contentLayoutRect.size
            if newSize != context.coordinator.lastReportedSize {
                context.coordinator.lastReportedSize = newSize
                onChange(newSize)
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator: NSObject {
        var lastReportedSize: CGSize = .zero
        var didSetInitialSize = false
    }
}
#endif
