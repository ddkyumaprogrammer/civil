import os
from json import loads, dumps
from requests import post
from django.conf import settings
from constance import config


def send_ultrafast_sms(**kwargs):
    data = {}
    params = []
    for key, value in kwargs.items():
        if key == 'mobile_num':
            data['Mobile'] = kwargs['mobile_num']
        elif key == 'template_id':
            data['TemplateId'] = kwargs['template_id']
        else:
            params.append({'Parameter': key, 'ParameterValue': value})
    if params:
        data['ParameterArray'] = params
    print(data)

    headers = {"Content-Type": "application/json", "x-sms-ir-secure-token": config.ACTIVE_TOKEN_KEY}
    try:
        r = post(settings.SMS_IR['FAST_SEND_URL'], dumps(data), headers=headers)

        # email = EmailMessage('ثبت سرویس','کاربر {} سرویس {} را ثبت کرد.'.format(kwargs['mobile_num'],kwargs['OrderType']) ,'karbamaregisterservice@gmail.com',['karbamabnd@gmail.com','mohammadbehnam72@gmail.com'],['karbamaregisterservice@gmail.com'])
        # email = EmailMessage('ثبت سرویس','کاربر {} سرویس {} را ثبت کرد.'.format(kwargs['mobile_num'],kwargs['OrderType']) ,'karbamaregisterservice@gmail.com',['bineiaz@gmail.com','s.n.bahador@gmail.com'],['karbamaregisterservice@gmail.com'])
        # email.send()

        response = loads(r.text)
        if response['IsSuccessful'] is True:
            print('sms sent successfully: {}'.format(response['IsSuccessful']))
            # param=[]
            # param.append({'Parameter': 'client', 'ParameterValue': '098528'})
            # data['ParameterArray'] = param
            #
            # data['Mobile'] = '09376100349'
            # r = post(settings.SMS_IR['FAST_SEND_URL'], dumps(data), headers=headers)

            return True
        elif response['Message'] == "Token منقضی شده است . Token جدیدی درخواست کنید":
            print('token expired: {}'.format(response['Message']))
        else:
            print(response)
    except Exception as e:
        print(e)
        return False


def get_image_path(instance, filename):
    return os.path.join('img', str(instance.category), filename)



