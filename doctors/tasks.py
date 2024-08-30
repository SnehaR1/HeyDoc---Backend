from celery.utils.log import get_task_logger
from django.core.mail import EmailMessage
from time import sleep
from django.core.mail import send_mail
from celery import shared_task

logger = get_task_logger(__name__)


@shared_task(name="send_email_task")
def send_mail_task(subject, message, email_from, recipient_list):
    send_mail(subject, message, email_from, recipient_list, fail_silently=False)
