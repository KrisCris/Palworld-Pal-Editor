#!/bin/bash
set -e

APPNAME="palworld-pal-editor"
APPDIR="./AppDir"
DISTDIR="./dist"
ARCH="x86_64"
APPIMAGE_NAME="$APPNAME-$ARCH.AppImage"
APPIMAGE_TOOL="./appimagetool-$ARCH.AppImage"

# Check for Node.js
if which npm > /dev/null; then
    NPM_CMD=npm
else
    echo "❌ Node.js (npm) is not installed."
    exit 1
fi

# Build frontend
echo "🚧 Building frontend..."
cd "./frontend/palworld-pal-editor-webui"
$NPM_CMD install
$NPM_CMD run build
cd ../../

# Move frontend build to Python package
rm -rf "./src/palworld_pal_editor/webui"
mv "./frontend/palworld-pal-editor-webui/dist" "./src/palworld_pal_editor/webui"

# Check for Python
if which python3 > /dev/null; then
    PYTHON_CMD=python3
elif which python > /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ Python is not installed."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version | awk '{print $2}')
PYTHON_MAJOR_VERSION=$(echo ${PYTHON_VERSION} | cut -d. -f1)
PYTHON_MINOR_VERSION=$(echo ${PYTHON_VERSION} | cut -d. -f2)

if [ "$PYTHON_MAJOR_VERSION" -lt 3 ] || { [ "$PYTHON_MAJOR_VERSION" -eq 3 ] && [ "$PYTHON_MINOR_VERSION" -lt 11 ]; }; then
    echo "❌ Python 3.11 or newer is required."
    exit 1
fi

echo "🐍 Using $PYTHON_CMD (version $PYTHON_VERSION)"

# Setup Python venv and install dependencies
$PYTHON_CMD -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install pyinstaller
pip install qtpy
pip install pyside6

# Clean previous build
rm -rf "$DISTDIR"
mkdir -p "$DISTDIR"

# Build with PyInstaller
echo "📦 Building with PyInstaller..."
pyinstaller --onefile \
  -i "./icon.ico" \
  --add-data="src/palworld_pal_editor/assets/data:assets/data" \
  --add-data="src/palworld_pal_editor/assets/icons:assets/icons" \
  --add-data="src/palworld_pal_editor/webui:webui" \
  ./src/palworld_pal_editor/__main__.py \
  --name "$APPNAME" \
  --hidden-import="pkg_resources.extern"

PYINSTALLER_BINARY="$DISTDIR/$APPNAME"

# Download appimagetool if not present
if [ ! -f "$APPIMAGE_TOOL" ]; then
    echo "⬇️  Downloading appimagetool..."
    curl -L -o "$APPIMAGE_TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
    chmod +x "$APPIMAGE_TOOL"
fi

# Prepare AppDir
echo "📁 Preparing AppImage structure..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib"
cp "$PYINSTALLER_BINARY" "$APPDIR/usr/bin/"

# Delete original binary
rm -f "$PYINSTALLER_BINARY"

# 🔧 Bundle necessary libraries (ldd-based)
echo "📎 Copying shared libraries..."
ldd "$APPDIR/usr/bin/$APPNAME" | awk '{print $3}' | grep -v '^(' | while read -r lib; do
    if [ -f "$lib" ]; then
        cp -v --parents "$lib" "$APPDIR/usr/lib/" 2>/dev/null || true
    fi
done

# Create AppRun
cat > "$APPDIR/AppRun" << EOF
#!/bin/bash
HERE="\$(dirname "\$(readlink -f "\$0")")"
export LD_LIBRARY_PATH="\$HERE/usr/lib:\$LD_LIBRARY_PATH"
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
"$APPIMAGE_TOOL" "$APPDIR" "$DISTDIR/$APPIMAGE_NAME"

echo "✅ Done! Output AppImage: $DISTDIR/$APPIMAGE_NAME"

