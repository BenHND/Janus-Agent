# Contributing to Janus

Thank you for your interest in contributing to Janus! This guide will help you get started.

## 📋 Table of Contents

- [Development Setup](#development-setup)
- [Project Dependencies](#project-dependencies)
- [Testing Guidelines](#testing-guidelines)
- [Security Guidelines](#security-guidelines)
- [Code Standards](#code-standards)
- [Pull Request Process](#pull-request-process)

## 🔧 Development Setup

### Prerequisites

- Python 3.8 or higher
- macOS 10.14+ (for full feature support)
- Git for version control

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/BenHND/Janus.git
cd Janus

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If available
```

For detailed installation instructions, see [Installation Guide](../user/01-installation.md).

## 📦 Project Dependencies

See [DEPENDENCIES.md](DEPENDENCIES.md) for a complete list of project dependencies, including:

- Core dependencies (Whisper, PyAutoGUI, etc.)
- Optional dependencies (LLM, Vision, TTS)
- Development dependencies
- System requirements

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_parser

# Run with verbose output
python -m unittest discover tests -v

# Run with coverage (if pytest-cov installed)
pytest --cov=janus tests/
```

### Writing Tests

- Write unit tests for all new functionality
- Follow existing test patterns in the `tests/` directory
- Aim for >80% code coverage for critical modules
- Include both positive and negative test cases
- Mock external dependencies (APIs, file system, etc.)

For more details, see [TESTING_GUIDE.md](TESTING_GUIDE.md).

## 🔒 Security Guidelines

Security is a top priority for Janus. Please follow these guidelines:

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities. Instead:

1. Email security concerns to [maintainer email]
2. Include detailed information about the vulnerability
3. Wait for acknowledgment before public disclosure

### Security Best Practices

- Never commit secrets, API keys, or credentials
- Always validate and sanitize user input
- Use parameterized queries for database operations
- Follow the principle of least privilege
- Keep dependencies up to date

For complete security guidelines, see [SECURITY_GUIDELINES.md](SECURITY_GUIDELINES.md).

## 📝 Code Standards

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and small (single responsibility)

### Documentation

- Comment complex logic and algorithms
- Update documentation when changing functionality
- Include usage examples in docstrings
- Keep README.md and docs up to date

### Git Commit Messages

```
type(scope): brief description

Detailed explanation of what changed and why.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## 🔄 Pull Request Process

### Before Submitting

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   python -m unittest discover tests
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat(module): add new feature"
   ```

### Submitting a Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request**
   - Go to the GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

3. **PR Description Should Include:**
   - What changed and why
   - Related issue numbers (Fixes #123)
   - Testing performed
   - Screenshots (if UI changes)
   - Breaking changes (if any)

### Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged

## 🤝 Community Guidelines

- Be respectful and constructive
- Help others in discussions
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md) (if available)
- Ask questions if you're unsure

## 📚 Additional Resources

- [Developer Documentation](../developer/00-README.md)
- [Architecture Guide](../developer/02-architecture.md)
- [Module Development Guide](../developer/03-module-development-guide.md)
- [User Documentation](../user/00-README.md)

## 💡 Need Help?

- Check existing [issues](https://github.com/BenHND/Janus/issues)
- Read the [documentation](../README.md)
- Ask questions in discussions or issues

---

Thank you for contributing to Janus! 🎉
