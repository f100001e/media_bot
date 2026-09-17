import os

from redis import Redis
from rq import Worker, Queue


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT
)

queue = Queue(
    "publisher",
    connection=redis_conn
)

worker = Worker(
    [queue],
    connection=redis_conn
)

if __name__ == "__main__":
    worker.work()