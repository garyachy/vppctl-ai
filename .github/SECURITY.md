# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in VPPctl AI, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly or use GitHub's private vulnerability reporting
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Considerations

### API Keys
- Never commit API keys to the repository
- Use environment variables for `OPENROUTER_API_KEY`
- Keep your API keys private and rotate them if exposed

### VPP Access
- This tool executes VPP CLI commands on your system
- Review suggested commands before execution
- Run with appropriate permissions only
- Do not use in production without understanding the commands

### Network Security
- API calls are made to OpenRouter's servers
- Ensure your network allows HTTPS connections to api.openrouter.ai
- Be aware that your queries are processed by external AI services

## Best Practices

1. Run VPPctl AI in isolated environments when testing
2. Review the `--dry-run` option for command preview without execution
3. Keep dependencies updated (`pip install -U -r requirements.txt`)
4. Monitor your API usage at openrouter.ai/keys
