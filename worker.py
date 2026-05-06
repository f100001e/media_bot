from redis import Redis
from rq import Worker, Queue
from queue.tasks import publish_job

redis_conn = Redis()
queue = Queue('publisher', connection=redis_conn)
worker = Worker([queue], connection=redis_conn)
worker.work()