import SwiftUI

struct ContentViewWindowSizeAccessor: View {
    let initialSize: CGSize
    let onChange: (CGSize) -> Void

    var body: some View {
        GeometryReader { geometry in
            Color.clear
                .preference(key: ContentViewWindowSizeKey.self, value: geometry.size)
        }
        .frame(width: initialSize.width, height: initialSize.height)
        .onPreferenceChange(ContentViewWindowSizeKey.self, perform: onChange)
    }
}

private struct ContentViewWindowSizeKey: PreferenceKey {
    static var defaultValue: CGSize = .zero

    static func reduce(value: inout CGSize, nextValue: () -> CGSize) {
        value = nextValue()
    }
}
