from django.conf.urls import url
from celery_sandbox.views import my_request, my_response

urlpatterns = [
    url(r'request/', my_request, name='celery-request'),
    url(r'response/', my_response, name='celery-response'),
]