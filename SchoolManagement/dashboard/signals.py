from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

# Set up logging
logger = logging.getLogger(__name__)
from .models import CustomUser, Student, Teacher

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            if instance.role == 'student':
                Student.objects.create(user=instance)
                logger.info(f"Student profile created for {instance.username}.")
            elif instance.role == 'teacher':
                Teacher.objects.create(user=instance)
                logger.info(f"Teacher profile created for {instance.username}.")
        except Exception as e:
            logger.error(f"Error creating profile for {instance.username}: {e}")

@receiver(post_save, sender=CustomUser)
def assign_admin_permissions(sender, instance, created, **kwargs):
    if created and instance.role == 'admin': 
        try:
            instance.is_staff = True 
            instance.is_superuser = True  
            instance.save()
            logger.info(f"Admin permissions assigned to {instance.username}.")
        except Exception as e:
            logger.error(f"Error assigning admin permissions to {instance.username}: {e}")



