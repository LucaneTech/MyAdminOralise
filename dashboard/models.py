from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Avg
from django.utils import timezone
from datetime import datetime, timedelta


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
     
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

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
        return static('profile_pics/profile.png')

# Modèle Profile unifié
class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_profile')
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        default='static/assets/img/profile.png',
        blank=True,
        null=True
    )
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    number = models.CharField(max_length=20)
    address = models.CharField(max_length=100)
    about = models.TextField(
        max_length=1000, 
        default=" "
    )
    theme_preference = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')

    def __str__(self):
        return f"Profile of {self.user.username}"

# Langues enseignées
class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

# Étudiant
class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=20, unique=True, editable=False)
    languages = models.ManyToManyField(Language, related_name='students')
    date_joined = models.DateField(default=timezone.now)
    total_hours_purchased = models.IntegerField(default=0)
    total_hours_used = models.IntegerField(default=0)
    current_teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_students')
    
    @property
    def hours_remaining(self):
        return self.total_hours_purchased - self.total_hours_used
    
    @property
    def recent_sessions(self):
        return Session.objects.filter(student=self).order_by('-date')[:5]
    
    @property
    def upcoming_sessions(self):
        today = timezone.now().date()
        return Session.objects.filter(
            student=self,
            date__gte=today,
            status='scheduled'
        ).order_by('date', 'start_time')
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.matricule})"

@receiver(pre_save, sender=Student)
def generate_student_matricule(sender, instance, **kwargs):
    if not instance.matricule:
        ecole_nom = "Oralise" 
        annee_courante = timezone.now().year
        
        dernier_etudiant = Student.objects.filter(
            matricule__startswith=f"{ecole_nom}-{annee_courante}-"
        ).order_by('-matricule').first()
        
        if dernier_etudiant:
            dernier_numero = int(dernier_etudiant.matricule.split('-')[-1])
            nouveau_numero = dernier_numero + 1
        else:
            nouveau_numero = 1
        
        instance.matricule = f"{ecole_nom}-{annee_courante}-{nouveau_numero:03d}"

# Enseignant
class Teacher(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    speciality = models.CharField(max_length=100)
    date_joined = models.DateField(default=timezone.now)
    languages = models.ManyToManyField(Language, related_name='teachers')
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    
    @property
    def total_students(self):
        return Student.objects.filter(current_teacher=self).count()
    
    @property
    def today_sessions(self):
        today = timezone.now().date()
        return Session.objects.filter(
            teacher=self,
            date=today,
            status='scheduled'
        ).order_by('start_time')
    
    @property
    def weekly_sessions(self):
        today = timezone.now().date()
        end_of_week = today + timedelta(days=7)
        return Session.objects.filter(
            teacher=self,
            date__gte=today,
            date__lte=end_of_week
        ).order_by('date', 'start_time')
    
    def __str__(self):
        return self.user.get_full_name()


# Compétences/Skills
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

# Notes
class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    mark = models.DecimalField(max_digits=4, decimal_places=2)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student} - {self.skill}: {self.mark}"

# Emploi du temps
class Schedule(models.Model): 
    DAY_CHOICES = [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
    ]

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    classroom = models.CharField(max_length=30, blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day', 'start_time']
        unique_together = ['day', 'skill', 'teacher', 'start_time']

    def __str__(self):
        return f"{self.skill.name} - {self.day} ({self.start_time} - {self.end_time})"
    
    @property
    def duration_minutes(self):
        """Retourne la durée du cours en minutes"""
        start = datetime.combine(datetime.min.date(), self.start_time)
        end = datetime.combine(datetime.min.date(), self.end_time)
        duration = end - start
        return int(duration.total_seconds() / 60)
    
    @property
    def language_name(self):
        """Retourne le nom de la langue associée au skill"""
        if self.language:
            return self.language.name
        elif self.skill and hasattr(self.skill, 'languages'):
            return self.skill.languages.first().name if self.skill.languages.exists() else "N/A"
        return "N/A"
    
    @property
    def color_class(self):
        """Retourne une classe CSS pour la couleur basée sur la langue"""
        if self.language:
            language_colors = {
                'Français': 'course-french',
                'Anglais': 'course-english',
                'Espagnol': 'course-spanish',
                'Allemand': 'course-german',
                'Italien': 'course-italian',
                'Chinois': 'course-chinese',
                'Japonais': 'course-japanese',
                'Arabe': 'course-arabic',
            }
            return language_colors.get(self.language.name, 'course-default')
        return 'course-default'

# Présence
class Attendance(models.Model):
    STATUS = (
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('late', 'En retard'),
        ('excused', 'Justifié'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS)
    arrival_time = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    session = models.ForeignKey('Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendances')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'skill', 'date')
        ordering = ['-date', 'student__user__first_name']
    
    def __str__(self):
        return f"{self.student} - {self.skill} - {self.date}: {self.status}"
    
    @property
    def is_late(self):
        """Vérifie si l'étudiant est en retard"""
        if self.arrival_time and self.session:
            return self.arrival_time > self.session.start_time
        return False
    
    @property
    def late_minutes(self):
        """Retourne le nombre de minutes de retard"""
        if self.is_late and self.session:
            start = datetime.combine(datetime.min.date(), self.session.start_time)
            arrival = datetime.combine(datetime.min.date(), self.arrival_time)
            delay = arrival - start
            return int(delay.total_seconds() / 60)
        return 0
    
    @classmethod
    def get_today_attendance_for_teacher(cls, teacher, date=None):
        """Récupère les présences du jour pour un enseignant"""
        if date is None:
            date = timezone.now().date()
        
        # Récupérer les séances du jour pour cet enseignant
        today_sessions = Session.objects.filter(
            teacher=teacher,
            date=date,
            status='scheduled'
        )
        
        # Récupérer les présences existantes
        attendances = cls.objects.filter(
            teacher=teacher,
            date=date
        ).select_related('student', 'skill', 'session')
        
        # Créer un dictionnaire des présences par étudiant et matière
        attendance_dict = {}
        for attendance in attendances:
            key = (attendance.student.id, attendance.skill.id)
            attendance_dict[key] = attendance
        
        return {
            'sessions': today_sessions,
            'attendances': attendance_dict,
            'date': date
        }

# Devoirs
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

# Séances de cours
class Session(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Prévue'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('rescheduled', 'Reportée'),
        ('absent', 'Absence')
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sessions')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='sessions')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    meeting_link = models.URLField(blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def duration_hours(self):
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        duration = end - start
        return duration.total_seconds() / 3600
    
    def __str__(self):
        return f"{self.student} - {self.language} - {self.date} ({self.get_status_display()})"
    
    class Meta:
        ordering = ['-date', '-start_time']

# Paiements
class Payment(models.Model):
    PAYMENT_TYPES = [
        ('hourly', 'À l\'heure'),
        ('package', 'Pack d\'heures'),
        ('subscription', 'Abonnement')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé')
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    hours_purchased = models.IntegerField()
    hours_remaining = models.IntegerField()
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    
    def __str__(self):
        return f"{self.student} - {self.amount}€ ({self.get_status_display()})"
    
    class Meta:
        ordering = ['-payment_date']

# Certificats
class Certificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='certificates')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    level = models.CharField(max_length=50)
    issued_date = models.DateField(auto_now_add=True)
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.student} - {self.language} - {self.level}"
    
    class Meta:
        ordering = ['-issued_date']

# Évaluations
class Evaluation(models.Model):
    EVALUATION_TYPES = [
        ('pronunciation', 'Prononciation'),
        ('grammar', 'Grammaire'),
        ('vocabulary', 'Vocabulaire'),
        ('fluency', 'Fluidité'),
        ('comprehension', 'Compréhension')
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='evaluations')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='evaluations')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    evaluation_type = models.CharField(max_length=20, choices=EVALUATION_TYPES)
    score = models.DecimalField(max_digits=4, decimal_places=2)
    comments = models.TextField(blank=True)
    evaluation_date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student} - {self.language} - {self.get_evaluation_type_display()}: {self.score}"
    
    class Meta:
        ordering = ['-evaluation_date']

# Ressources pédagogiques
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
    languages = models.ManyToManyField(Language, related_name='resources')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    skills = models.ManyToManyField(Skill, blank=True)  

    def __str__(self):
        return f"{self.uploaded_by.username} - {self.title}"

    class Meta:
        ordering = ['-created_at']

# Demandes/Réquêtes
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

# Notifications
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('session_reminder', 'Rappel de séance'),
        ('payment_due', 'Paiement dû'),
        ('certificate_ready', 'Certificat disponible'),
        ('evaluation_ready', 'Évaluation disponible'),
        ('system', 'Système')
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return f"{self.user} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']




#student comment about teacher 

class Comment(models.Model):
    comment = models.TextField(blank=True, null=True)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Note de 1 (mauvais) à 5 (excellent)"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    language = models.ForeignKey(
        'Language',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    comment_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'teacher', 'language')
        ordering = ['-comment_at']

    def __str__(self):
        return f"{self.student} → {self.teacher} ({self.rating}/5)"










@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'user_profile'):
        instance.user_profile.save()