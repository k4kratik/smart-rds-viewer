---
name: Bug report
about: Create a report to help us improve Smart RDS Viewer
title: '[BUG] '
labels: 'bug'
assignees: ''
---

## Bug Description

A clear and concise description of what the bug is.

## Environment

- **OS**: [e.g., macOS 13.0, Ubuntu 20.04, Windows 11]
- **Python Version**: [e.g., 3.9.7]
- **Smart RDS Viewer Version**: [e.g., 1.0.0]
- **AWS Region**: [e.g., ap-south-1]
- **AWS Profile Type**: [e.g., MFA-enabled, IAM role, access keys]

## Steps to Reproduce

1. Set environment variables:
   ```bash
   export AWS_PROFILE=your-profile
   export AWS_REGION=your-region
   ```
2. Run command: `smart-rds-viewer` or `smart-rds-viewer --nocache`
3. Perform action: [e.g., press 'u' to sort by usage]
4. See error

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

A clear and concise description of what actually happened.

## Error Output

```
Paste any error messages, stack traces, or console output here
```

## Screenshots

If applicable, add screenshots of the terminal output or UI issues.

## AWS Context

- **Number of RDS instances**: [approximate count]
- **Instance types affected**: [e.g., Aurora, MySQL, PostgreSQL]
- **Multi-AZ instances**: [Yes/No]
- **Regions with instances**: [list if multiple]

## Additional Context

Add any other context about the problem here. For example:
- Does this happen with fresh data only (`--nocache`)?
- Does this happen with cached data?
- Is this related to specific RDS instance configurations?
- Network connectivity issues?

## Possible Solution

If you have ideas on how to fix this, please share them here.