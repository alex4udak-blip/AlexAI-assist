/// OCR module for text extraction from images
/// Uses local OCR via Swift Vision framework on macOS with cloud fallback

use image::RgbaImage;
use serde::{Serialize, Deserialize};

/// OCR result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OcrResult {
    pub text: String,
    pub confidence: f32,
    pub language: Option<String>,
    pub bounding_boxes: Vec<BoundingBox>,
}

/// Text bounding box
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox {
    pub text: String,
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
    pub confidence: f32,
}

/// Extract text from image using local OCR
pub fn extract_text_from_image(image: &RgbaImage) -> Result<OcrResult, String> {
    #[cfg(target_os = "macos")]
    {
        extract_text_macos(image)
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("OCR only supported on macOS currently".to_string())
    }
}

/// Extract text from image file path
pub fn extract_text_from_path(path: &str) -> Result<OcrResult, String> {
    let image = image::open(path)
        .map_err(|e| format!("Failed to open image: {}", e))?;
    let rgba = image.to_rgba8();
    extract_text_from_image(&rgba)
}

/// Extract text using macOS Vision framework via Swift
#[cfg(target_os = "macos")]
fn extract_text_macos(image: &RgbaImage) -> Result<OcrResult, String> {
    use std::process::Command;
    use std::io::Write;

    // Save image to temporary file
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join(format!("observer_ocr_{}.png", uuid::Uuid::new_v4()));

    image.save(&temp_path)
        .map_err(|e| format!("Failed to save temp image: {}", e))?;

    // Create Swift script to perform OCR using Vision framework
    let swift_script = format!(
        r#"
import Foundation
import Vision
import AppKit

let imageURL = URL(fileURLWithPath: "{}")
guard let image = NSImage(contentsOf: imageURL) else {{
    print('{{"error": "Failed to load image"}}')
    exit(1)
}}

guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {{
    print('{{"error": "Failed to create CGImage"}}')
    exit(1)
}}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {{
    try handler.perform([request])

    if let observations = request.results {{
        var texts: [String] = []
        var boxes: [[String: Any]] = []

        for observation in observations {{
            guard let topCandidate = observation.topCandidates(1).first else {{ continue }}
            texts.append(topCandidate.string)

            let box: [String: Any] = [
                "text": topCandidate.string,
                "confidence": topCandidate.confidence,
                "x": observation.boundingBox.origin.x,
                "y": observation.boundingBox.origin.y,
                "width": observation.boundingBox.width,
                "height": observation.boundingBox.height
            ]
            boxes.append(box)
        }}

        let result: [String: Any] = [
            "text": texts.joined(separator: " "),
            "confidence": boxes.isEmpty ? 0.0 : boxes.map {{ ($0["confidence"] as? Float) ?? 0.0 }}.reduce(0.0, +) / Float(boxes.count),
            "bounding_boxes": boxes
        ]

        let jsonData = try JSONSerialization.data(withJSONObject: result, options: [])
        if let jsonString = String(data: jsonData, encoding: .utf8) {{
            print(jsonString)
        }}
    }} else {{
        print('{{"text": "", "confidence": 0.0, "bounding_boxes": []}}')
    }}
}} catch {{
    print('{{"error": "\(error.localizedDescription)"}}')
    exit(1)
}}
"#,
        temp_path.display()
    );

    // Write Swift script to temp file
    let script_path = temp_dir.join(format!("observer_ocr_{}.swift", uuid::Uuid::new_v4()));
    std::fs::write(&script_path, swift_script)
        .map_err(|e| format!("Failed to write Swift script: {}", e))?;

    // Execute Swift script
    let output = Command::new("swift")
        .arg(&script_path)
        .output()
        .map_err(|e| format!("Failed to execute Swift: {}", e))?;

    // Clean up temp files
    let _ = std::fs::remove_file(&temp_path);
    let _ = std::fs::remove_file(&script_path);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("OCR failed: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);

    // Parse JSON result
    let json: serde_json::Value = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("Failed to parse OCR result: {}", e))?;

    if let Some(error) = json.get("error") {
        return Err(format!("OCR error: {}", error));
    }

    let text = json.get("text")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let confidence = json.get("confidence")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0) as f32;

    let boxes: Vec<BoundingBox> = json.get("bounding_boxes")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|box_val| {
                    Some(BoundingBox {
                        text: box_val.get("text")?.as_str()?.to_string(),
                        confidence: box_val.get("confidence")?.as_f64()? as f32,
                        x: box_val.get("x")?.as_f64()? as f32,
                        y: box_val.get("y")?.as_f64()? as f32,
                        width: box_val.get("width")?.as_f64()? as f32,
                        height: box_val.get("height")?.as_f64()? as f32,
                    })
                })
                .collect()
        })
        .unwrap_or_default();

    Ok(OcrResult {
        text,
        confidence,
        language: None,
        bounding_boxes: boxes,
    })
}

/// Extract text using cloud OCR service (fallback)
pub async fn extract_text_cloud(image_base64: &str, api_key: &str) -> Result<OcrResult, String> {
    // Placeholder for cloud OCR integration
    // Could integrate with Google Cloud Vision, AWS Textract, or Azure Computer Vision

    let client = reqwest::Client::new();

    // Example using a generic OCR API endpoint
    let response = client
        .post("https://api.example.com/ocr")
        .header("Authorization", format!("Bearer {}", api_key))
        .json(&serde_json::json!({
            "image": image_base64,
        }))
        .send()
        .await
        .map_err(|e| format!("Cloud OCR request failed: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Cloud OCR failed with status: {}", response.status()));
    }

    let result: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse cloud OCR response: {}", e))?;

    // Parse response (format depends on provider)
    let text = result.get("text")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    Ok(OcrResult {
        text,
        confidence: 1.0,
        language: None,
        bounding_boxes: Vec::new(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ocr_result_creation() {
        let result = OcrResult {
            text: "Hello World".to_string(),
            confidence: 0.95,
            language: Some("en".to_string()),
            bounding_boxes: Vec::new(),
        };

        assert_eq!(result.text, "Hello World");
        assert_eq!(result.confidence, 0.95);
    }
}
