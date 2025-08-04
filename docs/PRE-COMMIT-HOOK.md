# 🔍 Pre-commit Hook Setup

This project includes a comprehensive pre-commit hook that validates your code before allowing commits.

## 📋 What the Hook Checks

### ✅ **Validation Steps**
1. **Python Syntax** - Compiles all `.py` files to check for syntax errors
2. **Project Structure** - Ensures all required files are present
3. **Import Validation** - Tests that all modules import correctly (if dependencies installed)
4. **Makefile Validation** - Verifies the build process works
5. **Quick Functionality Test** - Basic smoke test

### 📁 **Required Files Checked**
- `rds_viewer.py` - Main application
- `ui.py` - User interface components  
- `fetch.py` - RDS data fetching
- `metrics.py` - CloudWatch metrics
- `pricing.py` - AWS pricing API
- `requirements.txt` - Dependencies
- `README.md` - Documentation
- `Makefile` - Build automation

## 🚀 **Installation & Usage**

### **Automatic Installation**
The pre-commit hook is automatically installed in your local git repository at:
```
.git/hooks/pre-commit
```

### **Manual Testing**
You can test the hook manually without committing:
```bash
# Test the pre-commit hook
./.git/hooks/pre-commit

# Test the build process
make build
```

### **Typical Workflow**
```bash
# 1. Make your changes
git add *.py

# 2. Try to commit (hook runs automatically)
git commit -m "Add new feature"

# 3. If validation fails, fix issues and try again
# 4. If validation passes, commit proceeds
```

## 🔧 **Hook Output Examples**

### ✅ **Successful Validation**
```
🔍 Smart RDS Viewer - Pre-commit Validation
============================================
📋 Checking Python syntax...
✓ Python syntax check passed
📦 Checking project structure...
✓ All required files present
📊 Checking imports...
✓ All imports successful
🔧 Validating Makefile...
✓ Makefile build target works

🎉 Pre-commit validation successful!
✅ Commit approved - proceeding...
```

### ❌ **Failed Validation**
```
🔍 Smart RDS Viewer - Pre-commit Validation
============================================
📋 Checking Python syntax...
❌ Python syntax errors found
  File "rds_viewer.py", line 42
    def broken_function(
                       ^
SyntaxError: unexpected EOF while parsing
```

## ⚙️ **Configuration**

### **Bypassing the Hook** (Emergency Only)
```bash
# Skip pre-commit validation (NOT RECOMMENDED)
git commit --no-verify -m "Emergency commit"
```

### **Updating the Hook**
The hook is automatically updated when you pull changes to the repository.

### **Customization**
To modify the validation steps, edit:
```
.git/hooks/pre-commit
```

## 🎯 **Benefits**

- **Prevents Broken Commits** - Catches syntax errors before they reach the repository
- **Maintains Code Quality** - Ensures consistent project structure
- **Fast Feedback** - Immediate validation without CI/CD delays
- **Automated Checks** - No manual testing required
- **Team Consistency** - Same validation for all developers

## 🛠️ **Troubleshooting**

### **Hook Not Running**
```bash
# Check if hook exists and is executable
ls -la .git/hooks/pre-commit

# Make it executable if needed
chmod +x .git/hooks/pre-commit
```

### **Dependency Issues**
```bash
# Install dependencies for full validation
make install

# Or use virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **Permission Issues**
```bash
# Fix hook permissions
chmod +x .git/hooks/pre-commit
```

## 📊 **Integration with Make Commands**

The pre-commit hook leverages the project's Makefile:

```bash
make build      # Validate project (syntax, imports, tests)
make lint       # Run code quality checks  
make clean      # Clean build artifacts
make install    # Install dependencies
make run        # Run the application
make benchmark  # Run performance tests
```

---

**Note**: The pre-commit hook ensures code quality and prevents broken commits, making collaboration smoother and maintaining a stable main branch.