# Contributing to Janus

Thank you for your interest in contributing to Janus! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How Can I Contribute?

### Reporting Bugs

- Check if the issue has already been reported in the [Issues](https://github.com/BenHND/Janus/issues)
- Use the issue template if available
- Include detailed steps to reproduce the issue
- Provide system information (OS version, Python version, etc.)

### Suggesting Enhancements

- Open an issue with the "enhancement" label
- Clearly describe the feature and its benefits
- Explain why this feature would be useful to most users

### Contributing Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write or update tests as needed
5. Ensure all tests pass
6. Commit your changes with clear messages
7. Push to your fork
8. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- macOS (for full functionality)
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Janus.git
cd Janus

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -e ".[dev,test]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=janus tests/
```

### Running the Application

```bash
# CLI mode
janus

# Or using the main script
python -m apps.cli.main
```

## Pull Request Process

1. **Update Documentation**: Update the README.md or relevant docs if you change functionality
2. **Add Tests**: New features should include tests
3. **Code Style**: Follow PEP 8 and use the project's linting tools
4. **Commit Messages**: Write clear, concise commit messages
5. **Pull Request Description**: Clearly describe what your PR does and why

### PR Title Format

Use conventional commit format:
- `feat: Add new feature`
- `fix: Fix bug in module`
- `docs: Update documentation`
- `refactor: Refactor code`
- `test: Add tests`
- `chore: Update dependencies`

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints where possible
- Maximum line length: 100 characters
- Use Black for code formatting
- Use isort for import sorting

### Code Formatting

```bash
# Format code with Black
black janus/

# Sort imports with isort
isort janus/

# Check with flake8
flake8 janus/

# Type checking with mypy
mypy janus/
```

### Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings
- Keep comments clear and concise
- Update docs when changing functionality

### Testing

- Write unit tests for new functionality
- Aim for high test coverage
- Use meaningful test names
- Keep tests focused and isolated

## Project Structure

```
Janus/
├── janus/              # Core package
│   ├── runtime/        # Core orchestration
│   ├── capabilities/   # Agents and tools
│   ├── ai/            # LLM clients and reasoning
│   ├── vision/        # Vision and OCR
│   ├── io/            # Input/output (STT, TTS)
│   └── ...
├── apps/              # Applications
├── tests/             # Test suite
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## Questions?

Feel free to open an issue with the "question" label if you need help or clarification.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
