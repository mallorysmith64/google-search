"""Basic connection example.
"""

import redis

r = redis.Redis(
    host='redis-12907.c238.us-central1-2.gce.cloud.redislabs.com',
    port=12907,
    decode_responses=True,
    username="default",
    password="mEKAkLijrr9Yo8PUjQaKmv1wgLQ5Q0f4",
)

success = r.set('foo', 'bar')
# True

result = r.get('foo')
print(result)
# >>> bar


