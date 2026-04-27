#!/bin/bash
# ============================================================================
# Filmeto - macOS Build Script
# Produces: dist/Filmeto.app
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

cd "$PROJECT_ROOT"

print_info "========================================"
print_info "  Building Filmeto for macOS"
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

# Icon (convert PNG to ICNS if needed)
if [[ -f "$PROJECT_ROOT/textures/filmeto.icns" ]]; then
    PYINSTALLER_ARGS+=(--icon "$PROJECT_ROOT/textures/filmeto.icns")
else
    print_warn "No .icns icon found, using default PySide6 icon"
fi

# Bundle required data folders
for folder in agent app i18n server style textures utils; do
    if [[ -d "$folder" ]]; then
        PYINSTALLER_ARGS+=(--add-data "$folder:$folder")
    fi
done

print_info "Running PyInstaller ..."
pyinstaller "${PYINSTALLER_ARGS[@]}"

# Copy resources that PyInstaller might miss
if [[ -d "$DIST_DIR/$APP_NAME.app" ]]; then
    RESOURCES_DIR="$DIST_DIR/$APP_NAME.app/Contents/Resources"
    for folder in i18n style textures; do
        if [[ -d "$PROJECT_ROOT/$folder" ]]; then
            cp -r "$PROJECT_ROOT/$folder" "$RESOURCES_DIR/"
        fi
    done
fi

print_ok "Build complete: $DIST_DIR/$APP_NAME.app"
print_info "To test: open $DIST_DIR/$APP_NAME.app"
