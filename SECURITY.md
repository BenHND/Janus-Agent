# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Janus seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do not report security vulnerabilities through public GitHub issues.**

### How to Report

Please report security vulnerabilities by emailing:

**security@janus-project.org** (or create a private security advisory on GitHub)

### What to Include

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- We will acknowledge receipt of your vulnerability report within 3 business days
- We will provide a detailed response indicating next steps within 7 business days
- We will keep you informed about our progress towards a fix
- We will notify you when the vulnerability is fixed

### Disclosure Policy

- Once a security vulnerability has been fixed, we will publish a security advisory
- We follow responsible disclosure principles
- We will credit researchers who report vulnerabilities (unless they prefer to remain anonymous)

## Security Best Practices

When using Janus:

1. **Keep Dependencies Updated**: Regularly update Janus and its dependencies
2. **Review Permissions**: Janus requires system automation permissions - review what it can access
3. **API Keys**: Store API keys securely in `.env` file (never commit to version control)
4. **Network Security**: If using remote LLM providers, ensure secure connections
5. **Voice Commands**: Be aware that voice commands can trigger system actions
6. **Microphone Access**: Understand that Janus requires microphone access when active

## Known Security Considerations

### Voice Command Risks

- Voice commands can execute system actions
- Risk-based confirmation system helps prevent accidental dangerous actions
- Review the risk scoring in `janus/safety/validation/`

### Data Privacy

- All voice processing happens locally by default
- Optional crash reporting can be disabled in `config.ini`
- Voice recordings are not saved by default (can be enabled for debugging)

### LLM Integration

- When using cloud LLM providers (OpenAI, Anthropic), commands are sent to their APIs
- Use local LLM options for maximum privacy
- API keys should be stored in `.env` file, never committed

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed. Updates will be announced:

- In GitHub Security Advisories
- In release notes
- On the project README

Thank you for helping keep Janus and its users safe!
