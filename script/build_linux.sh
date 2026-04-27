#!/bin/bash
# ============================================================================
# Filmeto - Linux Build Script
# Produces: dist/Filmeto/  (optionally packaged as AppImage)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

cd "$PROJECT_ROOT"

print_info "========================================"
print_info "  Building Filmeto for Linux"
print_info "========================================"

ensure_venv
install_build_deps
cleanup

PYINSTALLER_ARGS=(
    "$MAIN_ENTRY"
    --name "$APP_NAME"
    --onedir
    --windowed
    --noconfirm
    --clean
    --distpath "$DIST_DIR"
    --workpath "$BUILD_DIR"
)

# Icon
if [[ -f "$PROJECT_ROOT/textures/filmeto.png" ]]; then
    PYINSTALLER_ARGS+=(--icon "$PROJECT_ROOT/textures/filmeto.png")
else
    print_warn "No icon found, using default PySide6 icon"
fi

# Bundle required data folders
for folder in agent app i18n server style textures utils; do
    if [[ -d "$folder" ]]; then
        PYINSTALLER_ARGS+=(--add-data "$folder:$folder")
    fi
done

print_info "Running PyInstaller ..."
pyinstaller "${PYINSTALLER_ARGS[@]}"

print_ok "Build complete: $DIST_DIR/$APP_NAME/"
print_info "To test: $DIST_DIR/$APP_NAME/$APP_NAME"

# ============================================================================
# Optional: Package as AppImage
# Requires: appimagetool (https://github.com/AppImage/AppImageKit)
# Usage: ./script/build_linux.sh --appimage
# ============================================================================

if [[ "${1}" == "--appimage" ]]; then
    print_info "Packaging as AppImage ..."

    if ! command -v appimagetool &>/dev/null; then
        print_error "appimagetool not found. Install it first:"
        print_error "  wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        print_error "  chmod +x appimagetool-x86_64.AppImage"
        print_error "  sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool"
        exit 1
    fi

    APPIMAGE_DIR="$DIST_DIR/AppImage"
    mkdir -p "$APPIMAGE_DIR/usr/bin"
    mkdir -p "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps"

    # Copy bundled app into AppImage structure
    cp -r "$DIST_DIR/$APP_NAME/"* "$APPIMAGE_DIR/usr/bin/"

    # Desktop entry
    cat > "$APPIMAGE_DIR/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Name=$APP_NAME
Exec=$APP_NAME
Type=Application
Categories=AudioVideo;
Icon=$APP_NAME
EOF

    # Icon
    if [[ -f "$PROJECT_ROOT/textures/filmeto.png" ]]; then
        cp "$PROJECT_ROOT/textures/filmeto.png" "$APPIMAGE_DIR/$APP_NAME.png"
        cp "$PROJECT_ROOT/textures/filmeto.png" "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    fi

    # AppRun entry point
    cat > "$APPIMAGE_DIR/AppRun" <<'APPRUN'
#!/bin/bash
SELF="$(readlink -f "$0")"
HERE="$(dirname "$SELF")"
exec "$HERE/usr/bin/Filmeto/Filmeto" "$@"
APPRUN
    chmod +x "$APPIMAGE_DIR/AppRun"

    appimagetool "$APPIMAGE_DIR" "$DIST_DIR/$APP_NAME-$APP_VERSION-x86_64.AppImage"
    rm -rf "$APPIMAGE_DIR"

    print_ok "AppImage created: $DIST_DIR/$APP_NAME-$APP_VERSION-x86_64.AppImage"
fi
