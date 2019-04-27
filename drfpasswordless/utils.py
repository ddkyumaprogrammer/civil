import logging
import os
from json import loads, dumps

from constance import config
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.template import loader
from django.utils import timezone
from requests import post

from civil import settings
from drfpasswordless.models import CallbackToken
from drfpasswordless.settings import api_settings


logger = logging.getLogger(__name__)
User = get_user_model()


def authenticate_by_token(callback_token):
    try:
        token = CallbackToken.objects.get(key=callback_token, is_active=True)

        # Returning a user designates a successful authentication.
        token.user = User.objects.get(pk=token.user.pk)
        token.is_active = False  # Mark this token as used.
        token.save()

        return token.user

    except CallbackToken.DoesNotExist:
        logger.debug("drfpasswordless: Challenged with a callback token that doesn't exist.")
    except User.DoesNotExist:
        logger.debug("drfpasswordless: Authenticated user somehow doesn't exist.")
    except PermissionDenied:
        logger.debug("drfpasswordless: Permission denied while authenticating.")

    return None


def create_callback_token_for_user(user, token_type):

    token = None
    token_type = token_type.upper()

    if token_type == 'EMAIL':
        token = CallbackToken.objects.create(user=user,
                                             to_alias_type=token_type,
                                             to_alias=getattr(user, api_settings.PASSWORDLESS_USER_EMAIL_FIELD_NAME))

    elif token_type == 'MOBILE':
        token = CallbackToken.objects.create(user=user,
                                             to_alias_type=token_type,
                                             to_alias=getattr(user, api_settings.PASSWORDLESS_USER_MOBILE_FIELD_NAME))

    if token is not None:
        return token

    return None


def validate_token_age(callback_token):
    """
    Returns True if a given token is within the age expiration limit.
    """
    try:
        token = CallbackToken.objects.get(key=callback_token, is_active=True)
        seconds = (timezone.now() - token.created_at).total_seconds()
        token_expiry_time = api_settings.PASSWORDLESS_TOKEN_EXPIRE_TIME

        if seconds <= token_expiry_time:
            return True
        else:
            # Invalidate our token.
            token.is_active = False
            token.save()
            return False

    except CallbackToken.DoesNotExist:
        # No valid token.
        return False


def verify_user_alias(user, token):
    """
    Marks a user's contact point as verified depending on accepted token type.
    """
    if token.to_alias_type == 'EMAIL':
        if token.to_alias == getattr(user, api_settings.PASSWORDLESS_USER_EMAIL_FIELD_NAME):
            setattr(user, api_settings.PASSWORDLESS_USER_EMAIL_VERIFIED_FIELD_NAME, True)
    elif token.to_alias_type == 'MOBILE':
        if token.to_alias == getattr(user, api_settings.PASSWORDLESS_USER_MOBILE_FIELD_NAME):
            setattr(user, api_settings.PASSWORDLESS_USER_MOBILE_VERIFIED_FIELD_NAME, True)
    else:
        return False
    user.save()
    return True


def inject_template_context(context):
    """
    Injects additional context into email template.
    """
    for processor in api_settings.PASSWORDLESS_CONTEXT_PROCESSORS:
        context.update(processor())
    return context


def send_email_with_callback_token(user, email_token, **kwargs):
    """
    Sends a Email to user.email.

    Passes silently without sending in test environment
    """

    try:
        if api_settings.PASSWORDLESS_EMAIL_NOREPLY_ADDRESS:
            # Make sure we have a sending address before sending.

            # Get email subject and message
            email_subject = kwargs.get('email_subject',
                                       api_settings.PASSWORDLESS_EMAIL_SUBJECT)
            email_plaintext = kwargs.get('email_plaintext',
                                         api_settings.PASSWORDLESS_EMAIL_PLAINTEXT_MESSAGE)
            email_html = kwargs.get('email_html',
                                    api_settings.PASSWORDLESS_EMAIL_TOKEN_HTML_TEMPLATE_NAME)

            # Inject context if user specifies.
            context = inject_template_context({'callback_token': email_token.key, })
            html_message = loader.render_to_string(email_html, context,)
            send_mail(
                email_subject,
                email_plaintext % email_token.key,
                api_settings.PASSWORDLESS_EMAIL_NOREPLY_ADDRESS,
                [getattr(user, api_settings.PASSWORDLESS_USER_EMAIL_FIELD_NAME)],
                fail_silently=False,
                html_message=html_message,)

        else:
            logger.debug("Failed to send token email. Missing PASSWORDLESS_EMAIL_NOREPLY_ADDRESS.")
            return False
        return True

    except Exception as e:
        logger.debug("Failed to send token email to user: %d."
                  "Possibly no email on user object. Email entered was %s" %
                  (user.id, getattr(user, api_settings.PASSWORDLESS_USER_EMAIL_FIELD_NAME)))
        logger.debug(e)
        return False


def send_sms_with_callback_token(user, mobile_token, **kwargs):
    """
    Sends a SMS to user.mobile via Twilio.

    Passes silently without sending in test environment.
    """
    base_string = kwargs.get('mobile_message', api_settings.PASSWORDLESS_MOBILE_MESSAGE)

    try:

        if api_settings.PASSWORDLESS_MOBILE_NOREPLY_NUMBER:
            # We need a sending number to send properly
            if api_settings.PASSWORDLESS_TEST_SUPPRESSION is True:
                # we assume success to prevent spamming SMS during testing.
                return True

            from twilio.rest import Client
            twilio_client = Client(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
            twilio_client.messages.create(
                body=base_string % mobile_token.key,
                to=getattr(user, api_settings.PASSWORDLESS_USER_MOBILE_FIELD_NAME),
                from_=api_settings.PASSWORDLESS_MOBILE_NOREPLY_NUMBER
            )
            return True
        else:
            logger.debug("Failed to send token sms. Missing PASSWORDLESS_MOBILE_NOREPLY_NUMBER.")
            return False
    except ImportError:
        logger.debug("Couldn't import Twilio client. Is twilio installed?")
        return False
    except KeyError:
        logger.debug("Couldn't send SMS."
                  "Did you set your Twilio account tokens and specify a PASSWORDLESS_MOBILE_NOREPLY_NUMBER?")
    except Exception as e:
        logger.debug("Failed to send token SMS to user: {}. "
                  "Possibly no mobile number on user object or the twilio package isn't set up yet. "
                  "Number entered was {}".format(user.id, getattr(user, api_settings.PASSWORDLESS_USER_MOBILE_FIELD_NAME)))
        logger.debug(e)
        return False




def custom_send_sms_with_callback_token(user, mobile_token, **kwargs):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(filename='/opt/w/civil/errors.log', level=logging.DEBUG)
    logging.debug("gf")
    if kwargs.get('token_expired'):
        token_headers = {"Content-Type": "application/json"}
        token_data = {"UserApiKey": settings.SMS_IR['USER_API_KEY'], "SecretKey": settings.SMS_IR['SECRET_KEY']}
        try:
            r = post(settings.SMS_IR['TOKEN_KEY_URL'], dumps(token_data), headers=token_headers)
            response = loads(r.text)
            if response['IsSuccessful'] is True:
                config.ACTIVE_TOKEN_KEY = response['TokenKey']
            else:
                print('token_key sms.ir error {}'.format(response['Message']))
                return False
        except Exception as e:
            print('token_key sms.ir error {}'.format(e))
            return False
    params = []
    data = {"TemplateId": 9460,
            "Mobile": getattr(user, api_settings.PASSWORDLESS_USER_MOBILE_FIELD_NAME)}
    params.append({'Parameter': "VerificationCode", 'ParameterValue': mobile_token.key})
    data['ParameterArray'] = params
    headers = {"Content-Type": "application/json", "x-sms-ir-secure-token": config.ACTIVE_TOKEN_KEY}
    print(data)
    print(headers)
    try:
        if api_settings.PASSWORDLESS_TEST_SUPPRESSION is True:
            return True
        r = post(settings.SMS_IR['FAST_SEND_URL'], dumps(data), headers=headers)
        response = loads(r.text)
        logging.debug (response)
        print(response)
        if response['IsSuccessful'] is True:
            print('sms sent successfully: {}'.format(response['IsSuccessful']))
            return True
        elif response['Message'] == "Token منقضی شده است . Token جدیدی درخواست کنید":
            print('token expired: {}'.format(response['Message']))
            custom_send_sms_with_callback_token(user, mobile_token, token_expired=True)
    except Exception as e:
        print(e)
        return False


# def send_app_link_sms(mobile_num, link):
#     data = {"ParameterArray": [{"Parameter": "Link", "ParameterValue": link}],
#             "Mobile": mobile_num,
#             "TemplateId": 1915}
#     headers = {"Content-Type": "application/json", "x-sms-ir-secure-token": config.ACTIVE_TOKEN_KEY}
#     try:
#         r = post(settings.SMS_IR['FAST_SEND_URL'], dumps(data), headers=headers)
#         response = loads(r.text)
#         if response['IsSuccessful'] is True:
#             print('sms sent successfully: {}'.format(response['IsSuccessful']))
#             return True
#         elif response['Message'] == "Token منقضی شده است . Token جدیدی درخواست کنید":
#             print('token expired: {}'.format(response['Message']))
#     except Exception as e:
#         print(e)
#         return False


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
    data['ParameterArray'] = params
    headers = {"Content-Type": "application/json", "x-sms-ir-secure-token": config.ACTIVE_TOKEN_KEY}
    try:
        r = post(settings.SMS_IR['FAST_SEND_URL'], dumps(data), headers=headers)
        response = loads(r.text)
        if response['IsSuccessful'] is True:
            print('sms sent successfully: {}'.format(response['IsSuccessful']))
            return True
        elif response['Message'] == "Token منقضی شده است . Token جدیدی درخواست کنید":
            print('token expired: {}'.format(response['Message']))
    except Exception as e:
        print(e)
        return False
