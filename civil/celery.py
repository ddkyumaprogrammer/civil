import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'civil.settings')

app = Celery('civil')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


# app.conf.beat_schedule = {
#     'refresh-sms-token-every-30-minutes': {
#         'task': 'drfpasswordless.tasks.refresh_sms_token',
#         'schedule': crontab(minute='*/20'),  # refresh every 20 minutes
#     },
# }
