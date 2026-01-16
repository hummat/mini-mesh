# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue
2. Email the maintainer directly (see [pyproject.toml](../pyproject.toml) for contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

You can expect:
- Acknowledgment within 48 hours
- Status update within 7 days
- Credit in the fix (unless you prefer anonymity)

## Security Considerations

### Docker Usage

The Docker image runs with:
- User-level permissions (not root)
- GPU access via nvidia-container-toolkit
- Mounted volumes for input/output data

### Environment Variables

- `WANDB_API_KEY`: If using Weights & Biases logging, this is forwarded into containers. Keep your API key secure.

### External Dependencies

This project depends on several external tools and libraries. Security updates to these dependencies are tracked via Dependabot.
