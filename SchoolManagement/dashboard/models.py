from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Avg
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('visitor', 'Visitor'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='visitor')

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def profile(self):
        return self.user_profile
    
    @property
    def profile_picture_url(self):
        if hasattr(self, 'user_profile') and self.user_profile.profile_picture:
            return self.user_profile.profile_picture.url
        return static('profile_pics/default.jpg')

# Modèle Profile unifié
class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_profile')
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        default='profile_pics/default.jpg',
        blank=True,
        null=True
    )
    city = models.CharField(max_length=50, default="Entrez votre ville")
    country = models.CharField(max_length=50, default="Entrez votre pays")
    address = models.CharField(max_length=100, default="Entrez votre adresse")
    about = models.TextField(
        max_length=1000, 
        default=" "
    )
    theme_preference = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')

    def __str__(self):
        return f"Profile of {self.user.username}"

# Type de formation (BTS, Licence, etc.)
class TrainingType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Filière
class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)
    type_formation = models.ForeignKey(TrainingType, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.type_formation.name})"

# Étudiant
class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=20, unique=True)
    branch = models.ManyToManyField('Branch')
    date_joined = models.DateField(default=timezone.now)
    
    @property
    def average(self):
        marks = Mark.objects.filter(student=self)
        if marks.exists():
            avg = marks.aggregate(Avg('mark'))['mark__avg']
            return round(avg, 2) if avg else 0
        return 0
    
    @property
    def attendance_rate(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        attendances = Attendance.objects.filter(
            student=self,
            date__gte=start_of_month,
            date__lte=today
        )
        if attendances.exists():
            present_count = attendances.filter(status='present').count()
            total_count = attendances.count()
            return round((present_count / total_count) * 100, 2)
        return 0
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.matricule})"

# Enseignant
class Teacher(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    speciality = models.CharField(max_length=100)
    date_joined = models.DateField(default=timezone.now)
    
    @property
    def total_students(self):
        return Student.objects.filter(skill__in=self.skill_set.all()).distinct().count()
    
    @property
    def total_courses(self):
        return self.skill_set.count()
    
    @property
    def total_assignments(self):
        return Assignment.objects.filter(skill__in=self.skill_set.all()).count()
    
    @property
    def monthly_attendance_stats(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        attendances = Attendance.objects.filter(
            skill__in=self.skill_set.all(),
            date__gte=start_of_month,
            date__lte=today
        )
        total = attendances.count()
        if total > 0:
            present = attendances.filter(status='present').count()
            late = attendances.filter(status='late').count()
            absent = attendances.filter(status='absent').count()
            return {
                'present_rate': round((present / total) * 100, 2),
                'late_rate': round((late / total) * 100, 2),
                'absent_rate': round((absent / total) * 100, 2)
            }
        return {'present_rate': 0, 'late_rate': 0, 'absent_rate': 0}
    
    @property
    def class_performance(self):
        skills = self.skill_set.all()
        marks = Mark.objects.filter(skill__in=skills)
        if marks.exists():
            avg = marks.aggregate(Avg('mark'))['mark__avg']
            return round(avg, 2) if avg else 0
        return 0
    
    def __str__(self):
        return self.user.get_full_name()

# Compétences
class Skill(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    teachers = models.ManyToManyField(Teacher)
    students = models.ManyToManyField(Student)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def average_mark(self):
        marks = Mark.objects.filter(skill=self)
        if marks.exists():
            avg = marks.aggregate(Avg('mark'))['mark__avg']
            return round(avg, 2) if avg else 0
        return 0
    
    def __str__(self):
        return self.name

class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    mark = models.DecimalField(max_digits=4, decimal_places=2)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student} - {self.skill}: {self.mark}"

class Schedule(models.Model): 
    DAY_CHOICES = [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    classroom = models.CharField(max_length=30, blank=True, null=True)  # J'ai renommé 'salle' en 'classroom'
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.branch.name} - {self.day} ({self.start_time} - {self.end_time})"

class Resource(models.Model):
    RESOURCE_TYPES = [
        ('document', 'Document'),
        ('link', 'Lien'),
        ('video', 'Vidéo'),
        ('other', 'Autre')
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/', null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    skills = models.ManyToManyField(Skill, related_name='resources')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assignments = models.ManyToManyField('Assignment', related_name='resources', blank=True)

    def __str__(self):
        return f"{self.uploaded_by.username} - {self.title}"

    class Meta:
        ordering = ['-created_at']

class Request(models.Model):
    REQUEST_TYPES = [
        ('absence', 'Justification d\'absence'),
        ('document', 'Demande de document'),
        ('meeting', 'Demande de rendez-vous'),
        ('other', 'Autre')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée')
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    attachment = models.FileField(upload_to='request_attachments/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.subject} ({self.get_status_display()})"

    class Meta:
        ordering = ['-created_at']

# Nouveaux modèles pour le dashboard enseignant
class Assignment(models.Model):
    TYPES = (
        ('homework', 'Devoir'),
        ('exam', 'Examen'),
        ('project', 'Projet'),
    )
    
    STATUS = (
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('closed', 'Terminé'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_late(self):
        return timezone.now() > self.due_date
    
    @property
    def submission_rate(self):
        total_students = self.skill.students.count()
        if total_students > 0:
            submissions = self.submissions.count()
            return round((submissions / total_students) * 100, 2)
        return 0
    
    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    mark = models.ForeignKey(Mark, on_delete=models.SET_NULL, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.assignment}"

    class Meta:
        unique_together = ['assignment', 'student']

class Attendance(models.Model):
    STATUS = (
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('late', 'En retard'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS)
    arrival_time = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('student', 'skill', 'date')
    
    def __str__(self):
        return f"{self.student} - {self.skill} - {self.date}: {self.status}"

# Signaux pour créer automatiquement les profils
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'user_profile'):
        instance.user_profile.save()