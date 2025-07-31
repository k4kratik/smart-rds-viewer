.PHONY: build clean install run help

# Default target
all: build

# Build the binary
build:
	@echo "🔨 Building Smart RDS Viewer binary..."
	@python3 build.py

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/ dist/ *.spec
	@echo "✓ Cleaned build artifacts"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@pip3 install -r requirements.txt
	@echo "✓ Dependencies installed"

# Run the Python version directly
run:
	@echo "🚀 Running Smart RDS Viewer..."
	@python3 rds_viewer.py

# Run the binary (if built)
run-binary:
	@echo "🚀 Running Smart RDS Viewer binary..."
	@./dist/smart-rds-viewer

# Show help
help:
	@echo "Smart RDS Viewer - Build Commands"
	@echo "=================================="
	@echo "make build      - Build the binary executable"
	@echo "make clean      - Clean build artifacts"
	@echo "make install    - Install Python dependencies"
	@echo "make run        - Run the Python version"
	@echo "make run-binary - Run the binary version (if built)"
	@echo "make help       - Show this help message" 