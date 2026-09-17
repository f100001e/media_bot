from redis import Redis
from rq import Queue, SimpleWorker
from rq.timeouts import TimerDeathPenalty

from publisher.tasks import REDIS_HOST, REDIS_PORT


class WindowsSimpleWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty


redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
)

queue = Queue(
    "publisher",
    connection=redis_conn,
)


if __name__ == "__main__":
    worker = WindowsSimpleWorker(
        [queue],
        connection=redis_conn,
    )

    worker.work()