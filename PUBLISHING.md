# 📦 Publishing Guide for Smart RDS Viewer

This guide explains how to publish Smart RDS Viewer to PyPI so users can install it with `pip install smart-rds-viewer`.

## 🏗️ Prerequisites

Before publishing, ensure you have:

1. **Updated package metadata** in `pyproject.toml`:
   - Author name and email
   - Repository URLs
   - Version number

2. **Required tools installed**:
   ```bash
   pip install build twine
   ```

3. **PyPI accounts created**:
   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

## 🔧 Build Distribution Files

First, clean and build fresh distribution files:

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build wheel distribution (recommended method)
pip wheel . --no-deps -w dist/

# Verify the build
ls -la dist/
```

Expected output:
```
smart_rds_viewer-1.0.0-py3-none-any.whl
```

## ✅ Validate Package

Before uploading, validate your package:

```bash
# Check package validity
twine check dist/*

# Expected output: "PASSED" for all files
```

## 🧪 Test Upload (TestPyPI)

**Always test on TestPyPI first!**

### Step 1: Upload to TestPyPI

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/smart_rds_viewer-1.0.0-py3-none-any.whl
```

You'll be prompted for:
- Username: Your TestPyPI username
- Password: Your TestPyPI password (or API token)

### Step 2: Test Installation

```bash
# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ smart-rds-viewer

# Test the command works
smart-rds-viewer --help
```

### Step 3: Clean Test Installation

```bash
# Remove test installation
pip uninstall smart-rds-viewer -y
```

## 🚀 Production Upload (PyPI)

Once testing is successful, upload to production PyPI:

```bash
# Upload to production PyPI
twine upload dist/smart_rds_viewer-1.0.0-py3-none-any.whl
```

## 🔐 Security: Using API Tokens

For better security, use API tokens instead of passwords:

### Create API Token

1. Go to PyPI Account Settings
2. Navigate to "API tokens"
3. Click "Add API token"
4. Set scope to "Entire account" or specific project
5. Copy the generated token

### Upload with Token

```bash
# Using API token (recommended)
twine upload --username __token__ --password <your-api-token> dist/smart_rds_viewer-1.0.0-py3-none-any.whl
```

## 🎉 After Publishing

Once published, users can install with:

```bash
pip install smart-rds-viewer
smart-rds-viewer
```

Your package will be available at:
- PyPI: https://pypi.org/project/smart-rds-viewer/
- TestPyPI: https://test.pypi.org/project/smart-rds-viewer/

## 🔄 Publishing Updates

For future releases:

### 1. Update Version

Edit `pyproject.toml`:
```toml
version = "1.1.0"  # Bump version
```

### 2. Rebuild and Test

```bash
# Clean and rebuild
rm -rf dist/
pip wheel . --no-deps -w dist/

# Test on TestPyPI first
twine upload --repository testpypi dist/smart_rds_viewer-1.1.0-py3-none-any.whl

# Then upload to production
twine upload dist/smart_rds_viewer-1.1.0-py3-none-any.whl
```

## 📋 Complete Workflow Summary

```bash
# 1. Clean and build
rm -rf dist/ build/ *.egg-info/
pip wheel . --no-deps -w dist/

# 2. Validate
twine check dist/*

# 3. Test upload
twine upload --repository testpypi dist/smart_rds_viewer-*.whl

# 4. Test install
pip install --index-url https://test.pypi.org/simple/ smart-rds-viewer
smart-rds-viewer --help
pip uninstall smart-rds-viewer -y

# 5. Production upload
twine upload dist/smart_rds_viewer-*.whl
```

## 🚨 Troubleshooting

### Common Issues

1. **"Package already exists"**
   - Version numbers cannot be reused
   - Increment version in `pyproject.toml`

2. **"Invalid package"**
   - Run `twine check dist/*` to see errors
   - Ensure all required metadata is filled

3. **Authentication issues**
   - Verify username/password
   - Consider using API tokens
   - Check if 2FA is enabled

### Package Metadata Checklist

Ensure these are set in `pyproject.toml`:
- [ ] name
- [ ] version
- [ ] description
- [ ] authors (with valid email)
- [ ] license
- [ ] dependencies
- [ ] entry points (console_scripts)

## 📚 Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)

---

**Ready to share your Smart RDS Viewer with the world! 🌍✨**