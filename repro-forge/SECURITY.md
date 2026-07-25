# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x.x   | 鉁?Active support   |
| 0.x.x   | 鈿狅笍 Best effort      |
| < 0.1.0 | 鉂?No support       |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, use the repository's [GitHub security page](https://github.com/selfrestart/26Summer/security).

We will acknowledge your report within 48 hours and provide a timeline for resolution within 5 business days.

### What to Include

- Type of vulnerability (e.g., code injection, data leak, dependency issue)
- Full reproduction steps
- Affected versions
- Impact assessment (if you have one)

### Process

1. You submit a report via email.
2. We confirm receipt within 48 hours.
3. We investigate and develop a fix.
4. We release a patch and publish a security advisory.
5. We credit you in the advisory (unless you prefer anonymity).

## Security Best Practices for Users

- **API Keys**: Never commit `.env` files. Use `.env.example` as a template.
- **Code Execution**: The Docker sandbox backend isolates generated code by default. Avoid using `--backend=local` with untrusted reproduction inputs.
- **Dependencies**: We run Dependabot weekly. Pin your dependencies in production.
- **File Uploads**: PDF files are processed in memory and not persisted to disk by default.

## Dependency Scanning

We use Dependabot to monitor dependencies. Critical CVEs are patched within 7 days.

