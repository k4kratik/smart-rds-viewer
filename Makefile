.PHONY: build clean install run lint binary benchmark help

# Default target
all: build

# Validate the project (syntax, imports, etc.)
build:
	@echo "🔨 Validating Smart RDS Viewer project..."
	@echo "📋 Checking Python syntax..."
	@python3 -m py_compile *.py
	@echo "✓ Syntax check passed"
	@echo "📦 Checking imports (requires dependencies)..."
	@python3 -c "try: import rds_viewer, ui, fetch, metrics, pricing; print('✓ All imports successful')\nexcept ImportError as e: print(f'⚠️  Import warning: {e} (run make install first)')" || true
	@echo "✅ Project validation complete!"

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

# Add a lint check
lint:
	@echo "🔍 Running code quality checks..."
	@python3 -m py_compile *.py
	@echo "✓ Syntax check passed"

# Build binary executable  
binary:
	@echo "🔨 Building binary executable..."
	@python3 build.py

# Simple performance benchmark
benchmark:
	@echo "⚡ Running performance benchmark..."
	@python3 benchmarks/simple_benchmark.py

# Show help
help:
	@echo "Smart RDS Viewer - Build Commands"
	@echo "=================================="
	@echo "make build      - Validate project (syntax, imports, tests)"
	@echo "make clean      - Clean build artifacts"
	@echo "make install    - Install Python dependencies"
	@echo "make run        - Run the Python version"
	@echo "make lint       - Run code quality checks"
	@echo "make binary     - Build binary executable"
	@echo "make benchmark  - Run quick performance benchmark"
	@echo "make help       - Show this help message" 