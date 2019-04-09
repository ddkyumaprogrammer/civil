import time
from celery import shared_task

@shared_task
def very_expensive_computation():
    time.sleep(10)
    return 42