#!/bin/bash
# Generate macOS rounded app icons from base icon.png

cd "$(dirname "$0")/icons"

# Check if icon.png exists
if [ ! -f "icon.png" ]; then
    echo "Error: icon.png not found in icons directory"
    exit 1
fi

echo "Generating macOS iconset..."

# Create iconset directory
mkdir -p icon.iconset

# Generate all required sizes using sips
sips -z 16 16 icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32 icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32 icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64 icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256 icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512 icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png

# Convert iconset to icns (macOS will apply rounded corners automatically)
iconutil -c icns icon.iconset -o icon.icns

# Cleanup
rm -rf icon.iconset

echo "Generated icon.icns successfully"
