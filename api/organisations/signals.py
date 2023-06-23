from datetime import datetime

from django.db.models.signals import pre_save
from django.dispatch import receiver

from organisations.models import Subscription
from users.models import FFAdminUser


@receiver(pre_save, sender=Subscription)
def send_alert_if_cancelled(sender, instance, *args, **kwargs):
    try:
        existing_object = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if (
        instance.cancellation_date
        and existing_object.cancellation_date != instance.cancellation_date
    ):
        FFAdminUser.send_alert_to_admin_users(
            subject=f"Organisation {instance.organisation.name} has cancelled their subscription",
            message=f'Organisation {instance.organisation.name} has cancelled their subscription on {datetime.strftime(instance.cancellation_date, "%Y-%m-%d %H:%M")}',
        )
