# 🚀 PyPI Setup Instructions

Follow these steps to set up your PyPI accounts and publish Smart RDS Viewer.

## 📝 Prerequisites Checklist

✅ Package metadata updated in `pyproject.toml`:
- [x] Author: Smart RDS Viewer 
- [x] Email: hello@kratik.dev
- [x] Repository URLs (update these with your actual repo)

## 🔐 Step 1: Create PyPI Accounts

### Test PyPI (Required for testing)
1. Go to: https://test.pypi.org/account/register/
2. Create an account with your email
3. Verify your email address

### Production PyPI (For official releases)  
1. Go to: https://pypi.org/account/register/
2. Create an account with the same email
3. Verify your email address

## 🔑 Step 2: Create API Tokens (Recommended)

### For TestPyPI:
1. Go to: https://test.pypi.org/manage/account/
2. Scroll to "API tokens"
3. Click "Add API token"
4. Name: `smart-rds-viewer-test`
5. Scope: "Entire account" 
6. **Save this token** - you'll need it for uploads

### For PyPI:
1. Go to: https://pypi.org/manage/account/
2. Scroll to "API tokens" 
3. Click "Add API token"
4. Name: `smart-rds-viewer`
5. Scope: "Entire account"
6. **Save this token** - you'll need it for production

## 🧪 Step 3: Test Upload to TestPyPI

```bash
# Build the package
make clean
make package

# Upload to TestPyPI using API token
twine upload --repository testpypi dist/smart_rds_viewer-1.0.0-py3-none-any.whl
# Username: __token__
# Password: <your-testpypi-api-token>

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ smart-rds-viewer
smart-rds-viewer --help

# Clean up test
pip uninstall smart-rds-viewer -y
```

## 🚀 Step 4: Production Upload to PyPI

Once testing is successful:

```bash
# Upload to production PyPI
twine upload dist/smart_rds_viewer-1.0.0-py3-none-any.whl
# Username: __token__  
# Password: <your-pypi-api-token>
```

## 🔄 GitHub Actions Setup

Your repository now has automated workflows:

### For Testing (on every push):
- `.github/workflows/test-build.yml` - Tests package building

### For Releases:
- `.github/workflows/release.yml` - Publishes to PyPI on tags

### To trigger a release:
```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

Or use the manual workflow dispatch in GitHub Actions.

## 🎯 Quick Commands Reference

```bash
# Build package
make package

# Check package validity  
twine check dist/*

# Upload to TestPyPI
twine upload --repository testpypi dist/*.whl

# Upload to PyPI
twine upload dist/*.whl

# Install from PyPI (after publishing)
pip install smart-rds-viewer
```

## 🎉 After Publishing

Your users can install with:
```bash
pip install smart-rds-viewer
smart-rds-viewer
```

Package will be available at:
- **PyPI**: https://pypi.org/project/smart-rds-viewer/
- **TestPyPI**: https://test.pypi.org/project/smart-rds-viewer/

---

**Ready to share your Smart RDS Viewer with the world! 🌍✨**