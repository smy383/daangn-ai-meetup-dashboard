// 사용: ocr <png>  → 한 줄에 하나씩 JSON {"t":글자,"x":중심x,"y":중심y,"w":폭,"h":높이} (원본 픽셀 좌표)
import Foundation
import Vision
import AppKit
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let W = Double(cg.width), H = Double(cg.height)
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages = ["ko-KR", "en-US"]
req.usesLanguageCorrection = false
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
for o in (req.results ?? []) {
  guard let c = o.topCandidates(1).first else { continue }
  let b = o.boundingBox
  let d: [String: Any] = ["t": c.string, "x": Int((b.midX) * W), "y": Int((1 - b.midY) * H),
                          "w": Int(b.width * W), "h": Int(b.height * H)]
  let j = try JSONSerialization.data(withJSONObject: d)
  print(String(data: j, encoding: .utf8)!)
}
