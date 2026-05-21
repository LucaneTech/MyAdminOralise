from django.db.models.signals import post_save, pre_save , post_delete
from django.dispatch import receiver
import logging
from django.db.models import Sum
from .models import CustomUser, Student, Teacher, Session, Payment, PaiementFormateur
from django.core.exceptions import ValidationError



# Set up logging
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
                is_staff=True,
                is_superuser=True
            )

        logger.info(f"Role sync done for {instance.username}")

    except Exception as e:
        logger.error(
            f"Error syncing role for {instance.username}: {e}",
            exc_info=True
        )



#Decrimentation of hours when session finished
@receiver(pre_save, sender=Session)
def store_old_session_status(sender, instance, **kwargs):
    if instance.pk:
        instance._old_status = Session.objects.filter(
            pk=instance.pk
        ).values_list('status', flat=True).first()
    else:
        instance._old_status = None


@receiver(post_save, sender=Session)
def deduct_student_hours_on_completion(sender, instance, **kwargs):
   
    if (
        instance._old_status != 'completed'
        and instance.status == 'completed'
    ):
        student = instance.student
        duration = instance.duration_hours 

       
        if student.hours_remaining < duration:
            raise ValidationError(
                f"{student} n'a plus assez d'heures disponibles."
            )
        
        student.total_hours_used += duration
        student.save(update_fields=['total_hours_used'])

        logger.info(
            f"{duration}h déduites pour {student} (Session {instance.id})"
        )




# Signal pour mettre à jour les heures de l'étudiant lors d'un paiement
@receiver(post_save, sender=Payment)
def update_student_hours_on_payment(sender, instance, created, **kwargs):
    """
    Met à jour les heures totales achetées de l'étudiant 
    quand un paiement est créé ou modifié
    """
    if instance.status == 'paid': 
        student = instance.student
        
        # Calculer la somme de toutes les heures achetées (paiements payés)
        total_purchased = Payment.objects.filter(
            student=student,
            status='paid'
        ).aggregate(total=Sum('hours_purchased'))['total'] or 0
        
        # Mettre à jour l'étudiant
        student.total_hours_purchased = total_purchased
        student.save()

@receiver(post_delete, sender=Payment)
def update_student_hours_on_payment_delete(sender, instance, **kwargs):
    """
    Met à jour les heures totales achetées de l'étudiant 
    quand un paiement est supprimé
    """
    if instance.status == 'paid':
        student = instance.student
        
        # Recalculer la somme des heures achetées
        total_purchased = Payment.objects.filter(
            student=student,
            status='paid'
        ).aggregate(total=Sum('hours_purchased'))['total'] or 0
        
        # Mettre à jour l'étudiant
        student.total_hours_purchased = total_purchased
        student.save()