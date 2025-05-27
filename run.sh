#!/bin/bash

# YouTube to MP3 Converter - One-Click Setup & Run Script
# This script sets up and runs the entire application locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    🎵 YouTube to MP3 Converter 🎵              ║"
    echo "║                      One-Click Setup & Run                    ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print step with icon
print_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

# Print success with icon
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Print warning with icon
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Print error with icon
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Print info with icon
print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate environment
validate_environment() {
    print_step "Validating environment..."
    
    # Detect operating system
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        print_info "Detected Windows environment"
        IS_WINDOWS=true
    else
        IS_WINDOWS=false
    fi
    
    # Check for Docker
    if ! command_exists docker; then
        print_error "Docker is not installed!"
        if [[ "$IS_WINDOWS" == "true" ]]; then
            print_info "Please install Docker Desktop from: https://docs.docker.com/desktop/install/windows/"
        else
            print_info "Please install Docker from: https://docs.docker.com/get-docker/"
        fi
        exit 1
    fi
    
    # Check for Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not installed!"
        if [[ "$IS_WINDOWS" == "true" ]]; then
            print_info "Docker Compose should be included with Docker Desktop"
            print_info "If not, install from: https://docs.docker.com/compose/install/"
        else
            print_info "Please install Docker Compose from: https://docs.docker.com/compose/install/"
        fi
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running!"
        if [[ "$IS_WINDOWS" == "true" ]]; then
            print_info "Please start Docker Desktop and try again."
        else
            print_info "Please start Docker and try again."
        fi
        exit 1
    fi
    
    print_success "Environment validation passed!"
}

# Setup environment variables
setup_environment() {
    print_step "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_info "Creating .env file..."
        cat > .env << EOF
# YouTube to MP3 Converter Configuration

# YouTube API Key (optional - for metadata)
# Get your API key from: https://console.developers.google.com/
YOUTUBE_API_KEY=your_youtube_api_key_here

# Application Settings
MAX_CONCURRENT_DOWNLOADS=3
CLEANUP_INTERVAL=3600
TEMP_DIR=/app/temp
STORAGE_DIR=/app/downloads

# Docker Platform (auto-detected)
PLATFORM=linux/arm64
BACKEND_URL=http://backend:8000

# Redis Configuration
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
EOF
        print_success "Created .env file with default settings"
        print_warning "You can edit .env to add your YouTube API key for better metadata"
    else
        print_success ".env file already exists"
    fi
    
    # Auto-detect platform
    if [[ $(uname -m) == "arm64" ]] || [[ $(uname -m) == "aarch64" ]]; then
        PLATFORM="linux/arm64"
        print_info "Detected ARM64 platform (Apple Silicon/ARM)"
    else
        PLATFORM="linux/amd64"
        print_info "Detected AMD64 platform (Intel/AMD)"
    fi
    
    # Update platform in .env file with proper escaping
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS (BSD sed)
        sed -i '' "s|PLATFORM=.*|PLATFORM=${PLATFORM}|" .env
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows (Git Bash/WSL)
        sed -i "s|PLATFORM=.*|PLATFORM=${PLATFORM}|" .env
    else
        # Linux (GNU sed)
        sed -i "s|PLATFORM=.*|PLATFORM=${PLATFORM}|" .env
    fi
    
    print_success "Platform set to: $PLATFORM"
}

# Create necessary directories
setup_directories() {
    print_step "Creating necessary directories..."
    
    # Create backend directories
    mkdir -p backend/temp backend/downloads backend/logs
    
    # Set permissions for directories
    chmod -R 755 backend/temp backend/downloads backend/logs
    
    print_success "Directories created and configured"
}

# Check available ports
check_ports() {
    print_step "Checking port availability..."
    
    # Check if ports are in use
    PORTS_IN_USE=""
    
    # Port checking method depends on OS
    if [[ "$IS_WINDOWS" == "true" ]]; then
        # Windows port checking
        if netstat -an | grep -q ":3000 "; then
            PORTS_IN_USE="$PORTS_IN_USE 3000"
        fi
        
        if netstat -an | grep -q ":8000 "; then
            PORTS_IN_USE="$PORTS_IN_USE 8000"
        fi
        
        if netstat -an | grep -q ":6379 "; then
            PORTS_IN_USE="$PORTS_IN_USE 6379"
        fi
    else
        # Unix-like systems (macOS, Linux)
        if command_exists lsof; then
            if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
                PORTS_IN_USE="$PORTS_IN_USE 3000"
            fi
            
            if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
                PORTS_IN_USE="$PORTS_IN_USE 8000"
            fi
            
            if lsof -Pi :6379 -sTCP:LISTEN -t >/dev/null 2>&1; then
                PORTS_IN_USE="$PORTS_IN_USE 6379"
            fi
        else
            # Fallback to netstat if lsof is not available
            if netstat -an | grep -q ":3000 "; then
                PORTS_IN_USE="$PORTS_IN_USE 3000"
            fi
            
            if netstat -an | grep -q ":8000 "; then
                PORTS_IN_USE="$PORTS_IN_USE 8000"
            fi
            
            if netstat -an | grep -q ":6379 "; then
                PORTS_IN_USE="$PORTS_IN_USE 6379"
            fi
        fi
    fi
    
    if [ -n "$PORTS_IN_USE" ]; then
        print_warning "The following ports are in use:$PORTS_IN_USE"
        print_warning "The application may not start correctly if these ports are occupied"
        echo -e "${YELLOW}Do you want to continue anyway? (y/N): ${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Please free up the ports and try again"
            exit 1
        fi
    else
        print_success "All required ports (3000, 8000, 6379) are available"
    fi
}

# Stop existing containers
stop_existing() {
    print_step "Stopping any existing containers..."
    
    # Use appropriate docker-compose command
    local compose_cmd="docker-compose"
    if ! command_exists docker-compose && docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    fi
    
    if $compose_cmd ps -q >/dev/null 2>&1; then
        $compose_cmd down >/dev/null 2>&1 || true
        print_success "Stopped existing containers"
    else
        print_info "No existing containers to stop"
    fi
}

# Build and run containers
build_and_run() {
    print_step "Building and starting containers..."
    print_info "This may take a few minutes on first run..."
    
    # Use appropriate docker-compose command
    local compose_cmd="docker-compose"
    if ! command_exists docker-compose && docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    fi
    
    # Export platform for docker-compose
    export PLATFORM=$PLATFORM
    export BACKEND_URL="http://backend:8000"
    
    # Build and start containers
    if $compose_cmd up --build -d; then
        print_success "Containers built and started successfully!"
    else
        print_error "Failed to build or start containers"
        print_info "Check the logs above for error details"
        exit 1
    fi
}

# Wait for services to be ready
wait_for_services() {
    print_step "Waiting for services to start..."
    
    # Wait for backend health check
    print_info "Waiting for backend service..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            print_success "Backend service is ready!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Backend service failed to start within 60 seconds"
            print_info "Check backend logs: docker-compose logs backend"
            exit 1
        fi
        
        echo -ne "${CYAN}⏳ Attempt $attempt/$max_attempts...${NC}\r"
        sleep 2
        ((attempt++))
    done
    
    # Wait for frontend
    print_info "Waiting for frontend service..."
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:3000 >/dev/null 2>&1; then
            print_success "Frontend service is ready!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Frontend service failed to start within 60 seconds"
            print_info "Check frontend logs: docker-compose logs frontend"
            exit 1
        fi
        
        echo -ne "${CYAN}⏳ Attempt $attempt/$max_attempts...${NC}\r"
        sleep 2
        ((attempt++))
    done
}

# Show final status
show_status() {
    # Use appropriate docker-compose command
    local compose_cmd="docker-compose"
    if ! command_exists docker-compose && docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    fi
    
    echo ""
    print_success "🎉 YouTube to MP3 Converter is now running!"
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                     📍 Service URLs                    ║${NC}"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║  🌐 Frontend (Web UI):   http://localhost:3000        ║${NC}"
    echo -e "${CYAN}║  🔧 Backend API:         http://localhost:8000        ║${NC}"
    echo -e "${CYAN}║  📊 API Health Check:    http://localhost:8000/health ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🚀 Open your browser and go to: ${YELLOW}http://localhost:3000${NC}"
    echo ""
    echo -e "${BLUE}📋 Useful Commands:${NC}"
    echo -e "${CYAN}  • View logs:        $compose_cmd logs -f${NC}"
    echo -e "${CYAN}  • Stop services:    $compose_cmd down${NC}"
    echo -e "${CYAN}  • Restart:          $compose_cmd restart${NC}"
    echo -e "${CYAN}  • View status:      $compose_cmd ps${NC}"
    echo ""
    
    # Show container status
    print_info "Container Status:"
    $compose_cmd ps
}

# Handle cleanup on exit
cleanup() {
    echo ""
    print_info "Script interrupted. Cleaning up..."
    exit 1
}

# Main execution
main() {
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM
    
    # Print banner
    print_banner
    
    # Use appropriate docker-compose command
    local compose_cmd="docker-compose"
    if ! command_exists docker-compose && docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    fi
    
    # Run setup steps
    validate_environment
    setup_environment
    setup_directories
    check_ports
    stop_existing
    build_and_run
    wait_for_services
    show_status
    
    # Keep the script running to show logs
    echo -e "${YELLOW}Press Ctrl+C to stop the application${NC}"
    echo ""
    
    # Follow logs
    $compose_cmd logs -f --tail=50
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
