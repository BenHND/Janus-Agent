# Secrets Management Policy

**Status:** ✅ Implemented
**Last Updated:** November 16, 2025
**Priority:** 🔴 CRITICAL

---

## Overview

This document outlines Janus's secrets management policy and implementation. All sensitive data such as API keys, tokens, and passwords must be handled according to these guidelines to prevent unauthorized access and security breaches.

---

## Table of Contents

1. [What Qualifies as a Secret](#what-qualifies-as-a-secret)
2. [Storage Guidelines](#storage-guidelines)
3. [Implementation Details](#implementation-details)
4. [Best Practices](#best-practices)
5. [CI/CD Integration](#cicd-integration)
6. [Incident Response](#incident-response)

---

## What Qualifies as a Secret

The following types of data are considered secrets and must be protected:

### API Keys and Tokens
- OpenAI API keys (`sk-...`)
- Anthropic API keys (`sk-ant-...`)
- Mistral AI API keys
- GitHub tokens (`ghp_...`, `gho_...`, etc.)
- AWS access keys (`AKIA...`)
- Bearer tokens
- OAuth tokens and refresh tokens

### Authentication Credentials
- Passwords
- Private keys (SSH, SSL/TLS certificates)
- Client secrets
- Authentication tokens

### Database Credentials
- Database passwords
- Connection strings with embedded credentials
- Encryption keys

### Other Sensitive Data
- Webhook URLs with authentication tokens
- Session secrets
- Encryption keys and salts
- PII (Personally Identifiable Information) in certain contexts

---

## Storage Guidelines

### ✅ Acceptable Storage Methods

1. **Environment Variables**
   - Store secrets in `.env` file (never committed to git)
   - Load via `python-dotenv` or similar libraries
   - Example:
     ```bash
     OPENAI_API_KEY=sk-your-secret-key-here
     ANTHROPIC_API_KEY=sk-ant-your-secret-key-here
     ```

2. **Secure Key Storage**
   - System keychain/keyring (macOS Keychain, Windows Credential Manager)
   - Encrypted files with restricted permissions
   - Dedicated secrets management services (AWS Secrets Manager, HashiCorp Vault)

3. **Encrypted Database Storage**
   - Use `janus.utils.encryption` module
   - Encryption keys stored separately from data
   - Example:
     ```python
     from janus.utils.encryption import get_encryption_service

     service = get_encryption_service()
     encrypted = service.encrypt("my_secret_value")
     ```

### ❌ Never Do This

1. **Never commit secrets to version control**
   - Don't hardcode API keys in source code
   - Don't commit `.env` files
   - Don't include secrets in configuration files

2. **Never log secrets**
   - Don't log API keys or tokens
   - Don't include secrets in exception messages
   - Don't dump sensitive data in debug output

3. **Never transmit secrets insecurely**
   - Don't send secrets in URL parameters
   - Don't include secrets in client-side code
   - Don't store secrets in plain text

---

## Implementation Details

### Automatic Secrets Filtering

Janus automatically filters secrets from logs and exception messages:

#### Logging
```python
from janus.logging import get_logger

logger = get_logger("my_module")

# Secrets are automatically filtered
logger.info(f"Using API key: {api_key}")  # api_key value will be redacted
logger.error("Failed with token: " + token)  # token will be redacted
```

#### Exceptions
```python
from janus.exceptions import JanusError

# Secrets in exception messages are automatically filtered
raise JanusError(f"API call failed with key {api_key}")
# Output: "API call failed with key ***REDACTED***"
```

### Manual Filtering

For explicit filtering in custom code:

```python
from janus.utils.secrets_filter import filter_secrets

# Filter a string
safe_message = filter_secrets("api_key=sk-1234567890")
# Result: "api_key=***REDACTED***"

# Filter a dictionary
safe_data = filter_secrets({
    "api_key": "secret123",
    "username": "john"
})
# Result: {"api_key": "***REDACTED***", "username": "john"}
```

### Database Encryption

For storing sensitive data in the database:

```python
from janus.utils.encryption import get_encryption_service

encryption = get_encryption_service()

# Encrypt sensitive data before storage
encrypted_key = encryption.encrypt(api_key)
db.store("api_key", encrypted_key)

# Decrypt when retrieving
decrypted_key = encryption.decrypt(stored_value)
```

### Configuration

Set encryption key via environment variable:
```bash
SPECTRA_ENCRYPTION_KEY=your-base64-encoded-fernet-key
```

Or let Janus generate and store a key automatically in `~/.janus/.encryption_key`.

---

## Best Practices

### Development

1. **Use `.env.example` as template**
   - Commit `.env.example` with placeholder values
   - Copy to `.env` and fill in real values
   - Never commit `.env`

2. **Verify `.gitignore`**
   - Ensure `.env` is in `.gitignore`
   - Add other secret-containing files
   - Use `git ls-files` to verify

3. **Use environment-specific secrets**
   - Development environment: Test/mock API keys
   - Production environment: Real API keys
   - Never mix production secrets in development

### Code Review

1. **Check for hardcoded secrets**
   - Review all string literals
   - Look for base64-encoded values
   - Check configuration files

2. **Verify secrets filtering**
   - Ensure logging uses filtered logger
   - Check exception messages
   - Review error handling

3. **Test with mock secrets**
   - Use fake API keys in tests
   - Verify filtering works correctly
   - Don't commit test secrets

### Production

1. **Rotate secrets regularly**
   - Change API keys periodically
   - Rotate encryption keys
   - Update access tokens

2. **Monitor for exposure**
   - Watch for leaked secrets
   - Use secret scanning tools
   - Set up alerts

3. **Limit secret access**
   - Principle of least privilege
   - Separate dev/prod secrets
   - Audit access logs

---

## CI/CD Integration

### GitHub Actions

Janus includes automated secret scanning in CI:

```yaml
# .github/workflows/secret-scan.yml
name: Secret Scanning
on: [push, pull_request]
jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: TruffleHog OSS
        uses: trufflesecurity/trufflehog@main
      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2
```

### Pre-commit Hooks

Install pre-commit hooks for local scanning:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: main
    hooks:
      - id: trufflehog
        args: ['--regex', '--entropy=False']
  - repo: https://github.com/gitleaks/gitleaks
    rev: latest
    hooks:
      - id: gitleaks
EOF

# Install hooks
pre-commit install
```

### Manual Scanning

Run manual scans periodically:

```bash
# Using TruffleHog
trufflehog filesystem . --only-verified

# Using Gitleaks
gitleaks detect --source . --verbose

# Using git-secrets
git secrets --scan
```

---

## Incident Response

### If a Secret is Exposed

1. **Immediate Actions (within 1 hour)**
   - Revoke/rotate the exposed secret immediately
   - Change the secret in all environments
   - Update `.env` files with new secret
   - Notify security team

2. **Investigation (within 24 hours)**
   - Identify scope of exposure
   - Check logs for unauthorized access
   - Determine how secret was exposed
   - Document timeline of events

3. **Remediation**
   - Remove secret from git history if committed
   - Update affected systems
   - Implement additional controls
   - Review and update policies

4. **Post-Incident**
   - Conduct retrospective
   - Update documentation
   - Improve detection mechanisms
   - Train team on best practices

### Reporting

If you discover an exposed secret:

1. **Don't panic**
2. **Don't commit fixes that include the secret**
3. **Report to:** security@janus.dev (or project maintainer)
4. **Include:**
   - Type of secret exposed
   - Location of exposure
   - Estimated time of exposure
   - Potential impact

---

## Testing

### Secrets Management Tests

Run the secrets management test suite:

```bash
python -m unittest tests.test_secrets_management -v
```

Tests cover:
- ✅ Secrets filtering in strings
- ✅ Secrets filtering in dictionaries
- ✅ Exception message filtering
- ✅ Log message filtering
- ✅ Encryption/decryption
- ✅ Integration with logger

### Manual Verification

Verify secrets are filtered:

```python
from janus.logging import get_logger
from janus.utils.secrets_filter import filter_secrets

# Test filtering
logger = get_logger("test")
test_key = "sk-test123456789012345678"

logger.info(f"Testing with key: {test_key}")
# Check log file - key should be redacted

filtered = filter_secrets(f"api_key={test_key}")
assert "***REDACTED***" in filtered
assert test_key not in filtered
```

---

## References

### Internal Documentation
- [Security Audit](../audit/03-code-quality-architecture.md)
- [Configuration Guide](../README.md)
- [Environment Variables](../../.env.example)

### External Resources
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)

### Tools
- [TruffleHog](https://github.com/trufflesecurity/trufflehog) - Secret scanner
- [Gitleaks](https://github.com/gitleaks/gitleaks) - Secret detection
- [git-secrets](https://github.com/awslabs/git-secrets) - Prevents committing secrets
- [detect-secrets](https://github.com/Yelp/detect-secrets) - Enterprise secret scanner

---

## Questions?

For questions about secrets management:

1. Check this documentation
2. Review the [Security Audit](../audit/03-code-quality-architecture.md)
3. Open an issue on GitHub
4. Contact the project maintainer

---

**Remember:** When in doubt, treat it as a secret and protect it!
