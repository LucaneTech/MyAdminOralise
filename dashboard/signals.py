from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
import logging
from django.db.models import Sum, F
from .models import CustomUser, Student, Teacher, Session, Payment, Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def sync_user_role(sender, instance, **kwargs):
    try:
        if instance.role == 'student':
            Student.objects.get_or_create(user=instance)
        elif instance.role == 'teacher':
            Teacher.objects.get_or_create(user=instance)
        elif instance.role == 'admin':
            CustomUser.objects.filter(pk=instance.pk).update(
                is_staff=True, is_superuser=True
            )
    except Exception as e:
        logger.error(f"Error syncing role for {instance.username}: {e}", exc_info=True)


@receiver(pre_save, sender=Session)
def store_old_session_status(sender, instance, **kwargs):
    if instance.pk:
        instance._old_status = Session.objects.filter(
            pk=instance.pk
        ).values_list('status', flat=True).first()
    else:
        instance._old_status = None


@receiver(post_save, sender=Session)
def handle_session_completed(sender, instance, **kwargs):
    if instance._old_status != 'completed' and instance.status == 'completed':
        hours = instance.duration_hours
        for student in instance.students.select_related('user').all():
            # Déduire les heures utilisées
            Student.objects.filter(pk=student.pk).update(
                total_hours_used=F('total_hours_used') + hours
            )
            # Notifier l'étudiant
            already_notified = Notification.objects.filter(
                user=student.user,
                notification_type='evaluation_request',
                message__contains=f"Session {instance.id}"
            ).exists()
            if not already_notified:
                Notification.objects.create(
                    user=student.user,
                    notification_type='evaluation_request',
                    title="Votre cours est terminé — donnez votre avis",
                    message=(
                        f"Votre séance de {instance.language} avec "
                        f"{instance.teacher} du {instance.date} est terminée. "
                        f"Session {instance.id} — Cliquez pour évaluer."
                    ),
                )
            logger.info(f"Notification évaluation créée pour {student} (Session {instance.id})")


@receiver(post_save, sender=Payment)
def update_student_hours_on_payment(sender, instance, created, **kwargs):
    if instance.status == 'paid':
        student = instance.student
        total_purchased = Payment.objects.filter(
            student=student, status='paid'
        ).aggregate(total=Sum('hours_purchased'))['total'] or 0
        student.total_hours_purchased = total_purchased
        student.save(update_fields=['total_hours_purchased'])


@receiver(post_delete, sender=Payment)
def update_student_hours_on_payment_delete(sender, instance, **kwargs):
    if instance.status == 'paid':
        student = instance.student
        total_purchased = Payment.objects.filter(
            student=student, status='paid'
        ).aggregate(total=Sum('hours_purchased'))['total'] or 0
        student.total_hours_purchased = total_purchased
        student.save(update_fields=['total_hours_purchased'])
