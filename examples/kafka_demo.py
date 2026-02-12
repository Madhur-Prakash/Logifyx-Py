"""
Kafka Logging Demo

Prerequisites:
1. Start Kafka: cd examples && docker-compose up -d
2. Run this script: python examples/kafka_demo.py
3. View logs: python examples/kafka_consumer.py
"""

from logify import Logify

# Create logger with Kafka streaming
log = Logify(
    name="kafka-demo",
    kafka_servers="localhost:9092",
    kafka_topic="app-logs",
    # Optional: Schema Registry for Avro validation
    schema_registry_url="http://localhost:8081",
    schema_compatibility="BACKWARD",
    color=True
)

# Send some test logs
log.info("Application started")
log.debug("Debug message with extra data")
log.warning("This is a warning")

try:
    result = 1 / 0
except Exception as e:
    log.error("Division error occurred", exc_info=True)

log.info("Application finished")

print("\n✅ Logs sent to Kafka topic 'app-logs'")
print("Run 'python examples/kafka_consumer.py' to see them")
