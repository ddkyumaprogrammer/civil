from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from celery_sandbox.tasks import very_expensive_computation


def my_request(request):

    return render(request, 'celery_sandbox_request.html')


def my_response(request):

    very_expensive_computation.delay()

    return render(request, 'celery_sandbox_response.html')