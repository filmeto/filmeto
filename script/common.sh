#!/bin/bash
# ============================================================================
# Filmeto - Shared build utilities (sourced by platform-specific scripts)
# ============================================================================

set -e

APP_NAME="Filmeto"
APP_VERSION="${FILMETO_VERSION:-0.1.0}"
MAIN_ENTRY="main.py"
ICON_PATH="textures/filmeto.png"

# Color output helpers
print_info()  { echo -e "\033[1;34m[INFO]\033[0m $*"; }
print_warn()  { echo -e "\033[1;33m[WARN]\033[0m $*"; }
print_error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }
print_ok()    { echo -e "\033[1;32m[OK]\033[0m $*"; }

# Locate project root (parent of the script/ directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"

ensure_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        VENV_PATH="$PROJECT_ROOT/.venv"
        if [[ ! -d "$VENV_PATH" ]]; then
            print_info "Creating virtual environment at $VENV_PATH ..."
            python3 -m venv "$VENV_PATH"
        fi
        print_info "Activating virtual environment ..."
        source "$VENV_PATH/bin/activate"
    else
        print_info "Using active virtual environment: $VIRTUAL_ENV"
    fi
}

install_build_deps() {
    print_info "Installing build dependencies ..."
    pip install --upgrade pip
    pip install pyinstaller
    pip install -r "$PROJECT_ROOT/requirements.txt"
}

cleanup() {
    print_info "Cleaning previous build artifacts ..."
    rm -rf "$BUILD_DIR" "$DIST_DIR"
}
