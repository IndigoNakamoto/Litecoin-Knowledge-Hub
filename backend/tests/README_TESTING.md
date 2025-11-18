# Testing Webhook Authentication

## Quick Start

### 1. Install Dependencies

```bash
# From project root
cd backend
pip install -r requirements.txt

# Or just install requests if you only need the test script
pip install requests
```

### 2. Set WEBHOOK_SECRET

```bash
# Generate a secret
export WEBHOOK_SECRET=$(openssl rand -base64 32)

# Or set it manually
export WEBHOOK_SECRET="your-secret-here"
```

### 3. Run the Test

```bash
# Use python3 (not python)
cd backend/tests
python3 test_webhook_auth.py

# Or with custom backend URL and secret
python3 test_webhook_auth.py http://localhost:8000 your-secret-here
```

## Common Issues

### "command not found: python"

**Solution:** Use `python3` instead of `python`:
```bash
python3 test_webhook_auth.py
```

### "ModuleNotFoundError: No module named 'requests'"

**Solution:** Install requests:
```bash
pip install requests
# or
pip3 install requests
```

### "WEBHOOK_SECRET not set"

**Solution:** Set the environment variable:
```bash
export WEBHOOK_SECRET="your-secret-here"
python3 test_webhook_auth.py
```

## Alternative: Run with Backend Virtual Environment

If you have a virtual environment for the backend:

```bash
# Activate virtual environment
cd backend
source venv/bin/activate  # or: source .venv/bin/activate

# Run test
cd tests
python test_webhook_auth.py  # python (not python3) works in venv
```

