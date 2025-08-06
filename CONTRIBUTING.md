# Contributing to Smart RDS Viewer

Thank you for your interest in contributing to Smart RDS Viewer! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

We welcome contributions of all kinds:
- 🐛 Bug reports and fixes
- ✨ New features and enhancements
- 📖 Documentation improvements
- 🧪 Tests and benchmarks
- 💡 Ideas and suggestions

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- AWS credentials configured
- Git installed

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/smart-rds-viewer.git
   cd smart-rds-viewer
   ```

2. **Set up Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Test the Installation**
   ```bash
   # Set required environment variables
   export AWS_PROFILE=your-profile
   export AWS_REGION=your-region
   
   # Run the application
   smart-rds-viewer
   ```

## 📋 Development Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Keep functions focused and modular

### Project Structure

```
smart-rds-viewer/
├── __main__.py               # Entry point
├── rds_viewer.py             # Main application logic
├── ui.py                     # Rich terminal UI components
├── fetch.py                  # RDS data fetching
├── metrics.py                # CloudWatch metrics
├── pricing.py                # AWS Pricing API
├── requirements.txt          # Dependencies
└── docs/                     # Documentation
```

### Commit Guidelines

**Important**: All commits must include a "Signed-off-by" line:

```bash
# Use the -s flag to automatically add sign-off
git commit -s -m "Add new feature for X"

# Or add manually to commit message:
# Signed-off-by: Your Name <your.email@example.com>
```

**Commit Message Format:**
```
type: brief description

Longer explanation if needed

Signed-off-by: Your Name <your.email@example.com>
```

**Types:**
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `perf:` Performance improvements

### Testing

Before submitting:

1. **Test the application manually**
   ```bash
   export AWS_PROFILE=your-profile
   export AWS_REGION=your-region
   python rds_viewer.py
   ```

2. **Run benchmarks** (if performance-related)
   ```bash
   python benchmarks/simple_benchmark.py
   ```

3. **Test with different scenarios**
   - Fresh data (no cache)
   - Cached data
   - Different AWS regions
   - Various RDS instance types

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment Information**
   - Python version
   - Operating system
   - AWS region
   - RDS instance types affected

2. **Steps to Reproduce**
   ```bash
   # Example
   export AWS_PROFILE=my-profile
   export AWS_REGION=us-east-1
   smart-rds-viewer --nocache
   # Error occurs when sorting by 'u' key
   ```

3. **Expected vs Actual Behavior**

4. **Error Messages**
   - Full stack trace if applicable
   - Console output

## ✨ Feature Requests

For new features:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** - why is this needed?
3. **Propose implementation** if you have ideas
4. **Consider backward compatibility**

### Feature Areas

- **UI Enhancements**: New columns, better formatting, themes
- **Performance**: Caching improvements, API optimizations
- **AWS Integration**: New metrics, additional services
- **Export/Import**: CSV export, configuration files
- **Monitoring**: Alerts, thresholds, notifications

## 🔧 Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow coding guidelines
   - Add tests if applicable
   - Update documentation

3. **Test Thoroughly**
   ```bash
   # Test with real AWS environment
   export AWS_PROFILE=your-profile
   export AWS_REGION=your-region
   python rds_viewer.py
   ```

4. **Commit with Sign-off**
   ```bash
   git commit -s -m "feat: add new sorting option for storage efficiency"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Description**
   - Clear title and description
   - Reference related issues
   - Include screenshots for UI changes
   - List testing performed

## 📁 Key Files to Know

### Core Application Files
- `rds_viewer.py` - Main application entry point
- `ui.py` - Rich terminal interface (800+ lines)
- `fetch.py` - RDS data fetching logic
- `metrics.py` - CloudWatch metrics handling
- `pricing.py` - AWS Pricing API integration

### Configuration Files
- `pyproject.toml` - Package configuration
- `requirements.txt` - Python dependencies
- `Makefile` - Build automation

### Documentation
- `README.md` - Main project documentation
- `docs/BENCHMARKING.md` - Performance benchmarks
- `docs/IMPROVEMENTS-1.md` - Development history

## 🧪 Testing Environment

### AWS Setup for Testing
```bash
# Required environment variables
export AWS_PROFILE=your-test-profile
export AWS_REGION=ap-south-1  # or your preferred region

# Test with cache
smart-rds-viewer

# Test without cache
smart-rds-viewer --nocache
```

### Performance Testing
```bash
# Run benchmark suite
python benchmarks/simple_benchmark.py

# Debug pricing issues
python scripts/debug_pricing.py

# Inspect pricing data
python scripts/inspect_pricing.py
```

## 🤖 AI Development Context

This project was developed with AI assistance (Claude Sonnet 4). When contributing:

- **Leverage AI tools** for code generation and debugging
- **Maintain code quality** - AI-generated code should be reviewed
- **Document AI assistance** in complex PRs if relevant
- **Focus on user experience** - the tool should be intuitive

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas
- **Documentation**: Check `docs/` folder for detailed guides

## 🙏 Recognition

Contributors will be acknowledged in:
- README.md acknowledgments section
- Release notes for significant contributions
- Git commit history (with proper attribution)

---

**Thank you for contributing to Smart RDS Viewer!** 🎉

Your contributions help make RDS monitoring better for developers everywhere.