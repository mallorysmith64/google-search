"""Basic connection example.
"""

import redis
import json

REDIS_HOST = 'redis-12907.c238.us-central1-2.gce.cloud.redislabs.com'
REDIS_PORT = 12907
REDIS_PASSWORD = "mEKAkLijrr9Yo8PUjQaKmv1wgLQ5Q0f4"

try:
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        username="default",
        password=REDIS_PASSWORD,
    )

    r.ping()
    print("Successfully connected to Redis")
    success = r.set("foo", "bar")
    print(f"'foo' to 'bar' successful: {success}")
    # True
    result = r.get("foo")
    print(f"Retrieved value for 'foo': {result}")

except redis.exceptions.ConnectionError as e:
    # This block handles failures where the client couldn't talk to the server (network, server down, wrong port/host).
    print(f"🛑 Connection Error: Could not reach Redis server at {REDIS_HOST}:{REDIS_PORT}. Is it running? Details: {e}")
    
