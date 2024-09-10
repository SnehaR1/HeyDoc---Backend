from celery.utils.log import get_task_logger
from django.core.mail import EmailMessage
from time import sleep
from django.core.mail import send_mail
from celery import shared_task
from twilio.rest import Client
from django.conf import settings

logger = get_task_logger(__name__)


@shared_task(name="send_email_task")
def send_mail_task(subject, message, email_from, recipient_list):
    send_mail(subject, message, email_from, recipient_list, fail_silently=False)


@shared_task(name="send_sms_task")
def send_sms_task(to, body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(body=body, from_=settings.TWILIO_PHONE_NUMBER, to=to)
