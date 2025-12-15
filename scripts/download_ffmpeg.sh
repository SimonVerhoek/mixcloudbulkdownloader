#!/bin/sh
#
# FFmpeg Binary Downloader (Bash Version)
#
# Downloads ffmpeg and ffprobe binaries for Windows and macOS platforms.
# - Windows binaries from gyan.dev (essentials build)
# - macOS binaries from evermeet.cx (direct downloads)
#
# Designed to work in Alpine Linux (docker/compose:latest) and other environments.
#

set -eu

# Configuration
WINDOWS_FFMPEG_URL="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
MACOS_FFMPEG_URL="https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.7z"
MACOS_FFPROBE_URL="https://evermeet.cx/ffmpeg/ffprobe-6.1.1.7z"
MACOS_ARM_FFMPEG_URL="https://www.osxexperts.net/ffmpeg80arm.zip"
MACOS_ARM_FFPROBE_URL="https://www.osxexperts.net/ffprobe80arm.zip"

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WINDOWS_DIR="$PROJECT_ROOT/app/resources/ffmpeg/windows"
MACOS_DIR="$PROJECT_ROOT/app/resources/ffmpeg/macos"
MACOS_INTEL_DIR="$PROJECT_ROOT/app/resources/ffmpeg/macos/intel"
MACOS_ARM_DIR="$PROJECT_ROOT/app/resources/ffmpeg/macos/arm64"

# Colors for output (if terminal supports them)
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
else
    RED="" GREEN="" YELLOW="" BLUE="" BOLD="" RESET=""
fi

log() {
    echo "${BLUE}[FFmpeg Download]${RESET} $*" >&2
}

log_error() {
    echo "${RED}[FFmpeg Download ERROR]${RESET} $*" >&2
}

log_success() {
    echo "${GREEN}[FFmpeg Download SUCCESS]${RESET} $*" >&2
}

log_warning() {
    echo "${YELLOW}[FFmpeg Download WARNING]${RESET} $*" >&2
}

# Progress display function
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '-'
    printf "] %d%% (%d/%d MB)" $percent $((current / 1024 / 1024)) $((total / 1024 / 1024))
}

# Download with progress (using wget or curl)
download_with_progress() {
    local url="$1"
    local output_file="$2"
    local max_retries=3
    
    attempt=1
    while [ $attempt -le $max_retries ]; do
        log "Downloading $url (attempt $attempt/$max_retries)"
        
        if command -v wget >/dev/null 2>&1; then
            # Use wget with progress bar
            if wget --progress=bar:force -O "$output_file" "$url" 2>&1; then
                echo
                local file_size
                if command -v stat >/dev/null 2>&1; then
                    # Try BSD stat first (macOS), then GNU stat (Linux)
                    file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null || echo "unknown")
                else
                    file_size="unknown"
                fi
                log "Downloaded $(basename "$output_file") ($file_size bytes)"
                return 0
            fi
        elif command -v curl >/dev/null 2>&1; then
            # Use curl with progress bar
            if curl -L --progress-bar -o "$output_file" "$url"; then
                echo
                local file_size
                if command -v stat >/dev/null 2>&1; then
                    # Try BSD stat first (macOS), then GNU stat (Linux)
                    file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null || echo "unknown")
                else
                    file_size="unknown"
                fi
                log "Downloaded $(basename "$output_file") ($file_size bytes)"
                return 0
            fi
        else
            log_error "Neither wget nor curl is available"
            return 1
        fi
        
        log_warning "Download attempt $attempt failed"
        if [ $attempt -lt $max_retries ]; then
            sleep 2
        fi
        attempt=$((attempt + 1))
    done
    
    log_error "Failed to download $url after $max_retries attempts"
    return 1
}

# Detect operating system
detect_os() {
    local os_name
    os_name=$(uname -s | tr '[:upper:]' '[:lower:]')
    
    case "$os_name" in
        linux)
            # Check if we're in CI targeting Windows
            if [ "${CI:-}" = "true" ] && echo "${CI_JOB_NAME:-}" | grep -qi windows; then
                echo "windows"
            else
                echo "linux"
            fi
            ;;
        darwin)
            echo "macos"
            ;;
        cygwin*|mingw*|msys*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Detect macOS architecture (Intel vs ARM64)
detect_macos_architecture() {
    local arch_name
    arch_name=$(uname -m)
    
    case "$arch_name" in
        x86_64)
            echo "intel"
            ;;
        arm64|aarch64)
            echo "arm64"
            ;;
        *)
            log_error "Unknown macOS architecture: $arch_name"
            echo "unknown"
            ;;
    esac
}

# Check and install dependencies
check_dependencies() {
    local missing_deps=""
    
    # Check for download tools
    if ! command -v wget >/dev/null 2>&1 && ! command -v curl >/dev/null 2>&1; then
        missing_deps="${missing_deps} wget-or-curl"
    fi
    
    # Check for unzip
    if ! command -v unzip >/dev/null 2>&1; then
        missing_deps="${missing_deps} unzip"
    fi
    
    # Check for 7z (for macOS downloads)
    if ! command -v 7z >/dev/null 2>&1 && ! command -v 7za >/dev/null 2>&1; then
        missing_deps="${missing_deps} 7z-or-7za"
    fi
    
    if [ -n "$missing_deps" ]; then
        log_error "Missing dependencies:$missing_deps"
        log "Installing missing dependencies..."
        
        # Try to install dependencies based on available package manager
        if command -v apk >/dev/null 2>&1; then
            # Alpine Linux
            apk add --no-cache wget unzip p7zip
        elif command -v apt-get >/dev/null 2>&1; then
            # Debian/Ubuntu
            apt-get update && apt-get install -y wget unzip p7zip-full
        elif command -v yum >/dev/null 2>&1; then
            # RHEL/CentOS
            yum install -y wget unzip p7zip
        elif command -v brew >/dev/null 2>&1; then
            # macOS with Homebrew
            brew install wget p7zip
        else
            log_error "Cannot install dependencies automatically. Please install:$missing_deps"
            return 1
        fi
    fi
}

# Extract Windows binaries from zip
extract_windows_binaries() {
    local zip_file="$1"
    local temp_dir
    temp_dir=$(mktemp -d)
    
    log "Extracting Windows binaries from $(basename "$zip_file")"
    
    # Extract zip file
    if ! unzip -q "$zip_file" -d "$temp_dir"; then
        log_error "Failed to extract zip file"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Find and copy binaries using a more portable approach
    local found_ffmpeg=false
    local found_ffprobe=false
    local files_list
    
    # Create temporary file list
    files_list=$(find "$temp_dir" -name "*.exe")
    
    # Process each file
    for file in $files_list; do
        local basename_file
        basename_file=$(basename "$file")
        
        if [ "$basename_file" = "ffmpeg.exe" ]; then
            cp "$file" "$WINDOWS_DIR/ffmpeg.exe"
            log "Installed ffmpeg.exe to $WINDOWS_DIR/ffmpeg.exe"
            found_ffmpeg=true
        elif [ "$basename_file" = "ffprobe.exe" ]; then
            cp "$file" "$WINDOWS_DIR/ffprobe.exe"
            log "Installed ffprobe.exe to $WINDOWS_DIR/ffprobe.exe"
            found_ffprobe=true
        fi
    done
    
    rm -rf "$temp_dir"
    
    if [ "$found_ffmpeg" = true ] && [ "$found_ffprobe" = true ]; then
        return 0
    else
        log_error "Could not find ffmpeg.exe and/or ffprobe.exe in the archive"
        return 1
    fi
}

# Extract macOS binary from 7z archive
extract_macos_7z() {
    local archive_file="$1"
    local binary_name="$2"
    local temp_dir
    temp_dir=$(mktemp -d)
    
    log "Extracting $binary_name from $(basename "$archive_file")"
    
    # Determine 7z command
    local extract_cmd
    if command -v 7z >/dev/null 2>&1; then
        extract_cmd="7z"
    elif command -v 7za >/dev/null 2>&1; then
        extract_cmd="7za"
    else
        log_error "No 7z extraction tool available"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Extract archive
    if ! "$extract_cmd" x "$archive_file" "-o$temp_dir" -y >/dev/null 2>&1; then
        log_error "Failed to extract 7z archive"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Find and copy binary
    local extracted_binary="$temp_dir/$binary_name"
    if [ -f "$extracted_binary" ]; then
        cp "$extracted_binary" "$MACOS_INTEL_DIR/$binary_name"
        chmod +x "$MACOS_INTEL_DIR/$binary_name"
        log "Installed $binary_name to $MACOS_INTEL_DIR/$binary_name"
        rm -rf "$temp_dir"
        return 0
    else
        log_error "Binary $binary_name not found in extracted archive"
        rm -rf "$temp_dir"
        return 1
    fi
}

# Extract macOS binary from zip archive
extract_macos_zip() {
    local zip_file="$1"
    local binary_name="$2"
    local temp_dir
    temp_dir=$(mktemp -d)
    
    log "Extracting $binary_name from $(basename "$zip_file")"
    
    # Extract zip file
    if ! unzip -q "$zip_file" -d "$temp_dir"; then
        log_error "Failed to extract zip file"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Find and copy binary
    local extracted_binary="$temp_dir/$binary_name"
    if [ -f "$extracted_binary" ]; then
        cp "$extracted_binary" "$MACOS_ARM_DIR/$binary_name"
        chmod +x "$MACOS_ARM_DIR/$binary_name"
        log "Installed $binary_name to $MACOS_ARM_DIR/$binary_name"
        rm -rf "$temp_dir"
        return 0
    else
        log_error "Binary $binary_name not found in extracted archive"
        rm -rf "$temp_dir"
        return 1
    fi
}

# Create cross-platform temporary file
create_temp_file() {
    local suffix="$1"
    if command -v mktemp >/dev/null 2>&1; then
        # Try GNU mktemp first (Linux/Alpine)
        if mktemp --suffix="$suffix" 2>/dev/null; then
            return 0
        fi
        # Fall back to BSD mktemp (macOS)
        local temp_file
        temp_file=$(mktemp)
        mv "$temp_file" "${temp_file}${suffix}"
        echo "${temp_file}${suffix}"
    else
        # Fallback for systems without mktemp
        local temp_file="/tmp/ffmpeg_download_$$_$(date +%s)${suffix}"
        touch "$temp_file"
        echo "$temp_file"
    fi
}

# Download Windows binaries
download_windows_binaries() {
    log "Downloading Windows binaries..."
    
    local temp_file
    temp_file=$(create_temp_file ".zip")
    
    if download_with_progress "$WINDOWS_FFMPEG_URL" "$temp_file"; then
        if extract_windows_binaries "$temp_file"; then
            rm -f "$temp_file"
            return 0
        fi
    fi
    
    rm -f "$temp_file"
    return 1
}

# Download macOS Intel binaries
download_macos_binaries() {
    log "Downloading macOS Intel binaries..."
    
    local temp_ffmpeg temp_ffprobe
    temp_ffmpeg=$(create_temp_file ".7z")
    temp_ffprobe=$(create_temp_file ".7z")
    
    local success=true
    
    # Download ffmpeg
    if download_with_progress "$MACOS_FFMPEG_URL" "$temp_ffmpeg"; then
        if ! extract_macos_7z "$temp_ffmpeg" "ffmpeg"; then
            success=false
        fi
    else
        success=false
    fi
    
    # Download ffprobe
    if download_with_progress "$MACOS_FFPROBE_URL" "$temp_ffprobe"; then
        if ! extract_macos_7z "$temp_ffprobe" "ffprobe"; then
            success=false
        fi
    else
        success=false
    fi
    
    rm -f "$temp_ffmpeg" "$temp_ffprobe"
    
    [ "$success" = true ]
}

# Download macOS ARM64 binaries
download_macos_arm_binaries() {
    log "Downloading macOS ARM64 binaries..."
    
    local temp_ffmpeg temp_ffprobe
    temp_ffmpeg=$(create_temp_file ".zip")
    temp_ffprobe=$(create_temp_file ".zip")
    
    local success=true
    
    # Download ffmpeg
    if download_with_progress "$MACOS_ARM_FFMPEG_URL" "$temp_ffmpeg"; then
        if ! extract_macos_zip "$temp_ffmpeg" "ffmpeg"; then
            success=false
        fi
    else
        success=false
    fi
    
    # Download ffprobe
    if download_with_progress "$MACOS_ARM_FFPROBE_URL" "$temp_ffprobe"; then
        if ! extract_macos_zip "$temp_ffprobe" "ffprobe"; then
            success=false
        fi
    else
        success=false
    fi
    
    rm -f "$temp_ffmpeg" "$temp_ffprobe"
    
    [ "$success" = true ]
}

# Main function
main() {
    log "Starting ffmpeg binary download..."
    log "Project root: $PROJECT_ROOT"
    
    # Detect OS
    local current_os
    current_os=$(detect_os)
    log "Detected OS: $current_os"
    
    # Check and install dependencies
    if ! check_dependencies; then
        log_error "Failed to install required dependencies"
        exit 1
    fi
    
    # Download for appropriate platform
    case "$current_os" in
        windows)
            if [ ! -d "$WINDOWS_DIR" ]; then
                log_error "Windows directory does not exist: $WINDOWS_DIR"
                exit 1
            fi
            if download_windows_binaries; then
                log_success "Windows binaries downloaded successfully!"
            else
                log_error "Failed to download Windows binaries"
                exit 1
            fi
            ;;
        macos)
            # Detect macOS architecture
            local macos_arch
            macos_arch=$(detect_macos_architecture)
            log "Detected macOS architecture: $macos_arch"
            
            case "$macos_arch" in
                intel)
                    if download_macos_binaries; then
                        log_success "macOS Intel binaries downloaded successfully!"
                    else
                        log_error "Failed to download macOS Intel binaries"
                        exit 1
                    fi
                    ;;
                arm64)
                    if download_macos_arm_binaries; then
                        log_success "macOS ARM64 binaries downloaded successfully!"
                    else
                        log_error "Failed to download macOS ARM64 binaries"
                        exit 1
                    fi
                    ;;
                unknown)
                    log_error "Cannot determine macOS architecture, unable to download appropriate binaries"
                    exit 1
                    ;;
                *)
                    log_error "Unsupported macOS architecture: $macos_arch"
                    exit 1
                    ;;
            esac
            ;;
        linux)
            log_warning "Linux detected. This script is designed for Windows and macOS binaries only."
            log "Please install ffmpeg through your system package manager."
            log_success "No action needed for Linux platform."
            ;;
        *)
            log_error "Unsupported operating system: $current_os"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"