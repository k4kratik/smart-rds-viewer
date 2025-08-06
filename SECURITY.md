# Security Policy

## Supported Versions

We provide security updates for the following versions of Smart RDS Viewer:

| Version | Supported | Status              |
| ------- | --------- | ------------------- |
| 1.x.x   | ✅        | Active development  |
| 0.x.x   | ❌        | No longer supported |

**Note**: We recommend always using the latest version available on PyPI for the most recent security fixes and improvements.

## Security Considerations

### AWS Credentials and Permissions

Smart RDS Viewer requires AWS credentials to function. Please follow these security best practices:

#### Credential Management

- **Never commit AWS credentials** to version control
- Use IAM roles when running on EC2 instances
- Use AWS profiles with MFA when possible
- Rotate access keys regularly
- Use temporary credentials (STS) when available

#### Required AWS Permissions

The application requires these minimum AWS permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "cloudwatch:GetMetricStatistics",
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Recommended Security Setup

```bash
# Use MFA-enabled profiles
export AWS_PROFILE=your-mfa-profile
export AWS_REGION=your-region

# Avoid using root credentials
# Create dedicated IAM user with minimal permissions
```

### Data Handling

#### Local Cache Security

- **Cache Location**: `/tmp/rds_pricing_cache.json`
- **Data Stored**: Pricing information only (no credentials)
- **Retention**: 24 hours automatic expiration
- **Permissions**: Readable only by the user who created it

#### Sensitive Information

The application handles:

- ✅ **Safe**: RDS instance metadata, pricing data, CloudWatch metrics
- ⚠️ **Caution**: Instance names may contain sensitive information
- ❌ **Never**: Database credentials, connection strings, or user data

### Network Security

#### API Endpoints

The application connects to these AWS endpoints:

- `rds.<region>.amazonaws.com` - RDS metadata
- `monitoring.<region>.amazonaws.com` - CloudWatch metrics
- `api.pricing.us-east-1.amazonaws.com` - Pricing data

#### HTTPS Only

All AWS API communications use HTTPS with certificate validation.

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### How to Report

1. **Do NOT create a public GitHub issue**
2. **Email security concerns** to: [hello@kratik.dev](mailto:hello@kratik.dev)
3. **Include the following information**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### What to Expect

- **Initial Response**: Within 48 hours
- **Confirmation**: We'll confirm if the issue is a valid security concern
- **Timeline**: Security fixes are prioritized and typically released within 7-14 days
- **Credit**: You'll be credited in the release notes (if desired)

### Security Update Process

1. **Assessment**: Evaluate severity and impact
2. **Fix Development**: Create and test security patch
3. **Release**: Publish updated version to PyPI
4. **Notification**: Update this document and release notes
5. **Advisory**: Create security advisory if warranted

## Security Best Practices for Users

### Installation Security

```bash
# Verify package integrity
pip install smart-rds-viewer

# Install from trusted sources only
# Avoid installing from unofficial repositories
```

### Runtime Security

```bash
# Run with minimal AWS permissions
export AWS_PROFILE=readonly-profile

# Use dedicated IAM user for monitoring
# Avoid using administrative credentials

# Clear cache if running on shared systems
rm -f /tmp/rds_pricing_cache.json
```

### Environment Security

- **Shared Systems**: Be aware that cache files are stored in `/tmp`
- **CI/CD**: Use service roles instead of long-lived access keys
- **Containers**: Mount credentials securely, avoid embedding in images
- **Logging**: Application logs don't contain sensitive data

## Known Security Considerations

### Cache Files

- **Location**: World-readable `/tmp` directory
- **Mitigation**: Files contain only pricing data, no credentials
- **Recommendation**: Clear cache on shared systems

### Error Messages

- **Behavior**: May include AWS account IDs in error messages
- **Mitigation**: Don't share error logs publicly without review
- **Recommendation**: Redact account-specific information when reporting issues

### Network Traffic

- **TLS**: All AWS API calls use HTTPS
- **Monitoring**: Network traffic may reveal AWS usage patterns
- **Recommendation**: Use VPC endpoints for additional security

## Security Updates History

| Date | Version | Description                           |
| ---- | ------- | ------------------------------------- |
| TBD  | 1.0.0   | Initial security policy establishment |

## Third-Party Dependencies

We regularly monitor our dependencies for security vulnerabilities:

### Core Dependencies

- **boto3**: AWS SDK - Updated regularly
- **rich**: Terminal UI - Stable, well-maintained
- **requests**: HTTP library - Security-focused maintenance

### Dependency Management

- Monitor security advisories for all dependencies
- Update dependencies promptly when security fixes are available
- Use `pip-audit` or similar tools to scan for vulnerabilities

## Compliance and Standards

### Data Protection

- **No PII**: Application doesn't collect or store personally identifiable information
- **AWS Data**: Only accesses metadata and metrics (no user data)
- **Logging**: Minimal logging, no sensitive data retention

### Industry Standards

- Follow OWASP guidelines for secure coding
- Implement least-privilege access principles
- Use secure communication protocols (TLS 1.2+)

---

**Security is a shared responsibility.** Please help us keep Smart RDS Viewer secure by following these guidelines and reporting any concerns promptly.

For general questions about security practices, please refer to the [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/) documentation.
