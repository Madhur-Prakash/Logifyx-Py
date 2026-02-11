"""
Kafka Log Consumer - View logs sent to Kafka

Usage: python examples/kafka_consumer.py
"""

import asyncio
import json
from aiokafka import AIOKafkaConsumer


async def consume_logs():
    consumer = AIOKafkaConsumer(
        'app-logs',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',  # Read from beginning
        group_id='log-viewer'
    )
    
    await consumer.start()
    print("🎧 Listening for logs on 'app-logs' topic...\n")
    print("=" * 60)
    
    try:
        async for msg in consumer:
            try:
                # Try to parse as JSON (fallback mode)
                log = json.loads(msg.value.decode('utf-8'))
            except:
                # Try Avro (skip magic byte + schema ID)
                try:
                    import fastavro
                    import io
                    from logify.kafka import LOG_SCHEMA_V1
                    from fastavro.schema import parse_schema
                    
                    # Skip 5 bytes (1 magic + 4 schema ID)
                    data = msg.value[5:] if msg.value[0] == 0 else msg.value
                    reader = io.BytesIO(data)
                    schema = parse_schema(LOG_SCHEMA_V1)
                    log = fastavro.schemaless_reader(reader, schema)
                except:
                    log = {"message": msg.value.decode('utf-8', errors='ignore')}
            
            # Pretty print the log
            level = log.get('level', 'INFO')
            level_colors = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',    # Red
                'CRITICAL': '\033[35m'  # Magenta
            }
            reset = '\033[0m'
            color = level_colors.get(level, '')
            
            print(f"{color}[{level}]{reset} {log.get('service', 'unknown')} - {log.get('message', '')}")
            print(f"       📍 {log.get('file', '')}:{log.get('line', '')} @ {log.get('timestamp', '')}")
            
            if log.get('exception'):
                print(f"       ❌ Exception:\n{log.get('exception')}")
            
            print("-" * 60)
            
    finally:
        await consumer.stop()


if __name__ == "__main__":
    print("\n📨 Kafka Log Consumer")
    print("Press Ctrl+C to stop\n")
    
    try:
        asyncio.run(consume_logs())
    except KeyboardInterrupt:
        print("\n\n👋 Consumer stopped")
