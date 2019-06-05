from civil.celery import app
from django.conf import settings
from constance import config
from json import loads, dumps
from requests import post
from jdatetime import datetime
from celery import Task


@app.task
def refresh_sms_token():

# for handler in logging.root.handlers[:]:
#     logging.root.removeHandler(handler)
# logging.basicConfig(filename='/opt/w/civil/error.log', level=logging.DEBUG)
# logging.debug("---------------------------------------------------")

    token_headers = {"Content-Type": "application/json"}
    token_data = {"UserApiKey": settings.SMS_IR['USER_API_KEY'], "SecretKey": settings.SMS_IR['SECRET_KEY']}
    try:
        r = post(settings.SMS_IR['TOKEN_KEY_URL'], dumps(token_data), headers=token_headers)
        response = loads(r.text)
        if response['IsSuccessful'] is True:
            config.ACTIVE_TOKEN_KEY = response['TokenKey']
            config.LAST_UPDATE = datetime.now()
            return 'Token key is {}'.format(response['TokenKey'])
        else:
            print('token_key sms.ir error {}'.format(response['Message']))
            return False
    except Exception as e:
        print('token_key sms.ir error {}'.format(e))
        return False
