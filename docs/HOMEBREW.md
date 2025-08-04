# 🍺 Homebrew Package

This repository includes a Homebrew formula for easy installation of Smart RDS Viewer.

## 📦 Installation

### Option 1: Install from Tap (Recommended)

```bash
# Add the tap
brew tap k4kratik/smart-rds-viewer

# Install the package
brew install smart-rds-viewer

# Run it
smart-rds-viewer
```

### Option 2: Install Directly

```bash
# Install directly from the formula
brew install k4kratik/smart-rds-viewer/smart-rds-viewer

# Run it
smart-rds-viewer
```

## 🔧 Development

### Update Formula

The formula is automatically updated by the GitHub workflow, but you can manually update it:

```bash
# Update formula for a specific version
ruby scripts/update-formula.rb 1.0.0
```

### Test Formula

```bash
# Test the formula locally
brew install --build-from-source deployment/Formula/smart-rds-viewer.rb
```

## 📋 Formula Details

- **Name**: `smart-rds-viewer`
- **Description**: Terminal companion for monitoring Amazon RDS instances
- **Homepage**: https://github.com/k4kratik/smart-rds-viewer
- **Supports**: macOS (Intel & Apple Silicon), Linux (AMD64 & ARM64)

## 🚀 Usage

After installation:

```bash
# Run the viewer
smart-rds-viewer

# Check version
smart-rds-viewer --version
```

## ⚙️ Requirements

- AWS credentials configured
- RDS, CloudWatch, and Pricing API permissions

## 🔄 Updates

The formula is automatically updated with each release. New versions will be available via:

```bash
brew upgrade smart-rds-viewer
``` 