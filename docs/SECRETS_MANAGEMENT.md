# Secrets Management Best Practices

## Overview

The NSA ReflexArc system implements comprehensive secrets management to protect API keys, credentials, and sensitive configuration data. This document outlines best practices for secure deployment and operation.

## API Key Configuration

### Required Providers

At least one AI provider must be configured:

- **OpenAI**: Set `OPENAI_API_KEY` environment variable
- **Anthropic**: Set `ANTHROPIC_API_KEY` environment variable  
- **Google Gemini**: Set `GOOGLE_API_KEY` environment variable
- **AWS Bedrock**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION`

### Key Format Validation

The system validates API key formats on startup:

- **OpenAI**: `sk-[a-zA-Z0-9]{48,}`
- **Anthropic**: `sk-ant-[a-zA-Z0-9_-]{95,}`
- **Google**: `[a-zA-Z0-9_-]{39}`
- **AWS Access Key**: `AKIA[0-9A-Z]{16}`
- **AWS Secret Key**: 40 characters
- **AWS Region**: Valid region format (e.g., `us-east-1`)

## Environment Variables

### Production Deployment

```bash
# Required: At least one AI provider
export OPENAI_API_KEY="sk-your-openai-key"
export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"

# AWS (all three required together)
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Optional: Custom encryption key for sensitive data
export NSA_ENCRYPTION_KEY="base64-encoded-key"

# Optional: CORS origins for web dashboard
export NSA_ALLOWED_ORIGINS="https://yourdomain.com,https://dashboard.example.com"
```

### Development Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys
nano .env

# Source the environment
source .env
```

## Encrypted Storage

### Overview

The system provides encrypted storage for sensitive data using AES-256 encryption via the `cryptography` library.

### Key Derivation

Encryption keys are derived using PBKDF2 with:
- **Algorithm**: SHA-256
- **Iterations**: 100,000
- **Salt**: Fixed system salt
- **Source**: System-specific data (hostname, user ID, home directory)

### Usage

```python
from utils.secrets_manager import secrets_manager

# Store encrypted secret
secrets_manager.store_encrypted_secret("api_token", "sensitive-value")

# Retrieve encrypted secret
token = secrets_manager.retrieve_encrypted_secret("api_token")
```

### Custom Encryption Key

For enhanced security, provide a custom encryption key:

```bash
# Generate a secure key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set as environment variable
export NSA_ENCRYPTION_KEY="your-generated-key"
```

## Key Rotation

### Automatic Monitoring

The system monitors API key age and usage:
- **Warning**: After 90 days
- **Required**: After 180 days

### Rotation Process

1. **Generate new API key** from provider
2. **Update environment variable** with new key
3. **Restart the system** to validate new key
4. **Revoke old key** from provider dashboard

### Rotation Checking

```python
from utils.secrets_manager import secrets_manager

# Check rotation status
rotation_needed = secrets_manager.check_key_rotation_needed()
for key, needs_rotation in rotation_needed.items():
    if needs_rotation:
        print(f"Key {key} requires rotation")
```

## Audit Logging

### Automatic Logging

All key operations are automatically logged:
- Key validation events
- Encrypted storage operations
- Key retrieval events
- Rotation warnings

### Audit Log Location

```
memory/secrets_audit.json
```

### Log Format

```json
{
  "OPENAI_API_KEY": {
    "first_use": 1703980800,
    "events": [
      {
        "timestamp": 1703980800,
        "event": "validation_success",
        "iso_time": "2024-01-01 00:00:00 UTC"
      }
    ]
  }
}
```

## Security Best Practices

### Environment Security

1. **Never commit API keys** to version control
2. **Use environment variables** for all secrets
3. **Restrict file permissions** on configuration files
4. **Use encrypted storage** for persistent secrets
5. **Rotate keys regularly** (every 90 days)

### Production Deployment

1. **Use container secrets** (Docker secrets, Kubernetes secrets)
2. **Enable audit logging** for compliance
3. **Monitor key usage** patterns
4. **Set up alerting** for rotation warnings
5. **Use least privilege** access for service accounts

### Network Security

1. **Enable HTTPS** for all API communications
2. **Configure CORS** properly for web dashboard
3. **Use rate limiting** to prevent abuse
4. **Validate content types** for all requests
5. **Implement proper authentication** for production

## Compliance Considerations

### Data Protection

- API keys are never logged in plaintext
- Encrypted storage uses industry-standard AES-256
- Audit logs track all key operations
- Key masking in logs and monitoring

### Regulatory Requirements

- **SOC 2**: Audit logging and key rotation
- **GDPR**: Encrypted storage and data minimization
- **HIPAA**: Encryption at rest and in transit
- **PCI DSS**: Key management and rotation

## Troubleshooting

### Startup Validation Failures

```bash
# Check environment variables
env | grep -E "(OPENAI|ANTHROPIC|GOOGLE|AWS)_"

# Validate key format manually
python -c "
import re
key = 'your-key-here'
if re.match(r'^sk-[a-zA-Z0-9]{48,}$', key):
    print('Valid OpenAI key format')
else:
    print('Invalid key format')
"
```

### Encryption Issues

```bash
# Check encryption key
python -c "
import os
key = os.getenv('NSA_ENCRYPTION_KEY')
if key:
    print(f'Custom key set: {key[:8]}...')
else:
    print('Using system-derived key')
"
```

### Permission Issues

```bash
# Fix memory directory permissions
chmod 700 memory/
chmod 600 memory/secrets_audit.json
chmod 600 memory/encrypted_secrets.dat
```

## Migration Guide

### From Plaintext to Encrypted Storage

```python
# Migrate existing secrets
from utils.secrets_manager import secrets_manager
import os

# Store existing environment variables in encrypted format
secrets_to_migrate = [
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY', 
    'GOOGLE_API_KEY'
]

for secret_name in secrets_to_migrate:
    value = os.getenv(secret_name)
    if value:
        secrets_manager.store_encrypted_secret(secret_name, value)
        print(f"Migrated {secret_name} to encrypted storage")
```

### Backup and Recovery

```bash
# Backup encrypted secrets
cp memory/encrypted_secrets.dat backup/secrets_$(date +%Y%m%d).dat
cp memory/secrets_audit.json backup/audit_$(date +%Y%m%d).json

# Restore from backup
cp backup/secrets_20240101.dat memory/encrypted_secrets.dat
cp backup/audit_20240101.json memory/secrets_audit.json
```

## Support

For additional security questions or issues:

1. Check the audit logs in `memory/secrets_audit.json`
2. Review system logs for validation errors
3. Verify environment variable configuration
4. Test key formats using the validation functions
5. Consult the troubleshooting section above