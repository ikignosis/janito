# Contributing

We welcome contributions to janito! This guide explains how to get involved.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/janito.git
   cd janito
   ```

3. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

4. **Set up development environment**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

5. **Make your changes** and test them

6. **Run tests**:
   ```bash
   pytest
   ```

7. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add feature: my new feature"
   ```

8. **Push to your fork**:
   ```bash
   git push origin feature/my-feature
   ```

9. **Open a Pull Request** on GitHub

## Code Guidelines

### Python Style

- Use 4 spaces for indentation
- Follow PEP 8 conventions
- Add type hints for function parameters and return values
- Write docstrings for all public functions and classes

### Example

```python
def greet_user(name: str, greeting: str = "Hello") -> str:
    """
    Generate a greeting message for a user.
    
    Args:
        name: The user's name
        greeting: The greeting word (default: "Hello")
    
    Returns:
        A formatted greeting string
    """
    return f"{greeting}, {name}!"
```

### Testing

- Write tests for new features
- Ensure all tests pass before submitting
- Aim for meaningful test coverage

```python
def test_greet_user():
    result = greet_user("Alice")
    assert result == "Hello, Alice!"
    
def test_greet_user_custom_greeting():
    result = greet_user("Bob", greeting="Hi")
    assert result == "Hi, Bob!"
```

## Types of Contributions

### Bug Fixes

- Describe the bug in detail
- Provide steps to reproduce
- Include test cases if applicable

### Features

- Explain the feature and its use case
- Provide examples of usage
- Consider backward compatibility

### Documentation

- Fix typos or unclear explanations
- Add examples or tutorials
- Translate or localize documentation

### Code Quality

- Refactor for clarity or performance
- Add type hints
- Improve test coverage

## Reporting Issues

When reporting issues, please include:

- Your operating system and version
- Python version
- janito version
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
