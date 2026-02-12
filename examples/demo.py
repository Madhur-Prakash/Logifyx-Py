"""
Logify Demo - Production-Grade Logging

This demo shows multiple usage patterns:
1. Direct instantiation (simple)
2. Global registration with get_logify_logger (recommended)
3. Context injection with ContextLoggerAdapter
"""

from logify import Logify, ContextLoggerAdapter, get_logify_logger, setup_logify


# ========================================
# Option 1: Direct Instantiation (Simple)
# ========================================
log = Logify(
    name="auth",
    mode="dev",
    file="auth.log",
    log_dir="logs",
    color=True,
    # remote_url="http://localhost:5000/logs",  # Uncomment with running server
    max_remote_retries=5,
    mask=True
)

log.info("Server started")
log.warning("password=123456 token=abcd123")  # Masked automatically
log.error("Login failed")


# ========================================
# Option 2: Global Registration (Recommended for large apps)
# ========================================
setup_logify()  # Call once at app startup

# Now use get_logify_logger anywhere in your app
api_log = get_logify_logger(
    "api", 
    mode="dev",
    file="api.log",
    log_dir="logs",
    color=True
)

api_log.info("API endpoint hit")


# ========================================
# Option 3: Context Injection (Request tracking)
# ========================================
# Wrap logger with context for request-scoped logging
request_log = ContextLoggerAdapter(
    log,
    {"request_id": "req-abc123", "user_id": 42}
)

request_log.info("User authenticated")
request_log.warning("Rate limit approaching")
request_log.error("Payment failed")
