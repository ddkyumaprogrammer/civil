# Create your views here.
from django.http.response import HttpResponse
from django.shortcuts import render
from celery_sandbox.tasks import refresh_sms_token


def my_request(request):

    return render(request, 'celery_sandbox_request.html')


def my_response(request):

    try:
        # eager = refresh_sms_token.apply()
        ee = refresh_sms_token()
        return render(request, 'celery_sandbox_response.html')
    except Exception as e:
        return HttpResponse(status=500)
