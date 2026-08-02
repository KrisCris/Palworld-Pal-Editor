#!/bin/bash
set -euo pipefail

APPNAME="palworld-pal-editor"
APPDIR="./AppDir"
DISTDIR="./dist"
ARCH="x86_64"
APPIMAGE_NAME="$APPNAME-$ARCH.AppImage"
APPIMAGE_TOOL="./appimagetool-$ARCH.AppImage"

if ! command -v npm > /dev/null; then
    echo "❌ Node.js (npm) is not installed."
    exit 1
fi
NPM_CMD=npm

# Build frontend
echo "🚧 Building frontend..."
cd "./frontend/palworld-pal-editor-webui"
$NPM_CMD ci
$NPM_CMD run build
cd ../../

# Move frontend build to Python package
rm -rf "./src/palworld_pal_editor/webui"
mv "./frontend/palworld-pal-editor-webui/dist" "./src/palworld_pal_editor/webui"

if command -v python3 > /dev/null; then
    PYTHON_CMD=python3
elif command -v python > /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ Python is not installed."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version | awk '{print $2}')
PYTHON_MAJOR_VERSION=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR_VERSION=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

if [ "$PYTHON_MAJOR_VERSION" -lt 3 ] || { [ "$PYTHON_MAJOR_VERSION" -eq 3 ] && [ "$PYTHON_MINOR_VERSION" -lt 11 ]; }; then
    echo "❌ Python 3.11 or newer is required."
    exit 1
fi

echo "🐍 Using $PYTHON_CMD (version $PYTHON_VERSION)"

# Set up Python venv and install the Linux GUI backend only for this artifact.
rm -rf venv
$PYTHON_CMD -m venv venv
source venv/bin/activate

python -m pip install -r requirements.txt
python -m pip install "pywebview[pyside6]==4.4.1"

# Clean previous build
rm -rf "$DISTDIR"
mkdir -p "$DISTDIR"

# Build with PyInstaller
echo "📦 Building with PyInstaller..."
pyinstaller --clean --noconfirm palworld-pal-editor.spec

PYINSTALLER_BINARY="$DISTDIR/$APPNAME"

# Download appimagetool if not present
if [ ! -f "$APPIMAGE_TOOL" ]; then
    echo "⬇️  Downloading appimagetool..."
    curl --fail --location --output "$APPIMAGE_TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
fi
chmod +x "$APPIMAGE_TOOL"

# Prepare AppDir
echo "📁 Preparing AppImage structure..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp "$PYINSTALLER_BINARY" "$APPDIR/usr/bin/"

# Delete original binary
rm -f "$PYINSTALLER_BINARY"

# Create AppRun
cat > "$APPDIR/AppRun" << EOF
#!/bin/bash
HERE="\$(dirname "\$(readlink -f "\$0")")"
export PYWEBVIEW_GUI="qt"
exec "\$HERE/usr/bin/$APPNAME" "\$@"
EOF
chmod +x "$APPDIR/AppRun"

# Create .desktop file
cat > "$APPDIR/$APPNAME.desktop" << EOF
[Desktop Entry]
Name=Palworld Pal Editor
Exec=$APPNAME
Icon=$APPNAME
Type=Application
Categories=Utility;
EOF

# Copy icon
cp "icon.png" "$APPDIR/$APPNAME.png"

# Build AppImage
echo "📦 Building AppImage..."
"$APPIMAGE_TOOL" --appimage-extract-and-run "$APPDIR" "$DISTDIR/$APPIMAGE_NAME"

echo "✅ Done! Output AppImage: $DISTDIR/$APPIMAGE_NAME"

