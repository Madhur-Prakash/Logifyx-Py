from logify import Logify

log = Logify(
    name="auth",
    mode="prod",
    file="auth.log",
    log_dir="logs",
    color=True,
    # remote_url="http://localhost:5000/logs",
    max_remote_retries=5,
    mask=True
)

log.info("Server started")
log.warning("password=123456 token=abcd123")
log.warning("password=123456 token=abcd123")
log.error("Login failed")
# log.error("Login failed")
# log.error("Login failed")
# log.error("Login failed")
# log.error("Login failed")
# log.error("Login failed")
# log.error("Login failed")
# log.warning("password=123456 token=abcd123")
# log.warning("password=123456 token=abcd123")
# log.warning("password=123456 token=abcd123")
