# Contributing to VPPctl AI

Thank you for your interest in contributing to VPPctl AI! This document provides guidelines and instructions for contributing.

## Ways to Contribute

- **Bug Reports**: Found a bug? Open an issue with details
- **Feature Requests**: Have an idea? We'd love to hear it
- **Code Contributions**: Fix bugs or implement new features
- **Documentation**: Improve docs, fix typos, add examples
- **Testing**: Test on different VPP versions and report results

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/vppctl-ai.git
   cd vppctl-ai
   ```
3. Set up the development environment:
   ```bash
   pip install -r requirements.txt
   export OPENROUTER_API_KEY="your-key"
   ```
4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Code Guidelines

### Python Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Keep the first line under 72 characters

Examples:
```
Add support for VPP 24.06 commands
Fix command parsing for show interfaces
Update documentation for API configuration
```

### Testing
- Test your changes with a running VPP instance
- Verify command validation works correctly
- Test with different AI models if possible

## Pull Request Process

1. Update documentation if needed
2. Test your changes thoroughly
3. Ensure your code follows the project style
4. Submit a pull request with a clear description
5. Link any related issues

## Reporting Bugs

When reporting bugs, please include:

- VPP version (`vppctl show version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant error messages or logs

## Feature Requests

For feature requests, please describe:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered
- How this benefits other users

## Questions?

- Open a GitHub issue for questions
- Check existing issues and documentation first

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
