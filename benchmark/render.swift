// Renders every page of a PDF to PNG with macOS PDFKit (fields' printed look included).
// swift render.swift in.pdf out_prefix dpi
import PDFKit
import AppKit
let a = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: a[1]))!
let dpi = CGFloat(Double(a[3])!)
for i in 0..<doc.pageCount {
    let page = doc.page(at: i)!
    let box = page.bounds(for: .mediaBox)
    let w = Int(box.width * dpi / 72), h = Int(box.height * dpi / 72)
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    let ctx = NSGraphicsContext(bitmapImageRep: rep)!
    NSGraphicsContext.current = ctx
    let cg = ctx.cgContext
    cg.setFillColor(NSColor.white.cgColor); cg.fill(CGRect(x: 0, y: 0, width: w, height: h))
    cg.scaleBy(x: dpi / 72, y: dpi / 72)
    page.draw(with: .mediaBox, to: cg)
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(a[2])-\(i + 1).png"))
}
print(doc.pageCount)
