from logify import Logify

log = Logify(
    name="auth",
    mode="prod",
    file="auth.log",
    log_dir="logs",
    color=True,
    remote_url="http://localhost:5000/logs",
    mask=True
).get_logger()

log.info("Server started")
log.warning("password=123456 token=abcd123")
log.error("Login failed")
