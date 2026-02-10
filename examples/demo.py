from logify import Logify

log = Logify(
    name="auth",
    preset="prod",
    file="auth.log",
    log_dir="qq",
    color=True,
    mask=True
).get_logger()

log.info("Server started")
log.warning("password=123456 token=abcd123")
log.error("Login failed")
