from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Avg
from django.utils import timezone
from datetime import datetime, timedelta
import re


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

   

    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,
        verbose_name="rôle"
    )

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

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
        return static('assets/img/profile.png')



class Profile(models.Model):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='user_profile',
        verbose_name="utilisateur"
    )
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        blank=True,
        null=True,
        verbose_name="photo de profil"
    )
    city = models.CharField(
        max_length=50,
        verbose_name="ville"
    )
    country = models.CharField(
        max_length=50,
        verbose_name="pays"
    )
    number = models.CharField(
        max_length=20,
        verbose_name="numéro de téléphone"
    )
    address = models.CharField(
        max_length=100,
        verbose_name="adresse"
    )
    about = models.TextField(
        max_length=1000, 
        default=" ",
        verbose_name="à propos"
    )
    theme_preference = models.CharField(
        max_length=10, 
        choices=[('light', 'Light'), ('dark', 'Dark')], 
        default='light',
        verbose_name="préférence de thème"
    )

    class Meta:
        verbose_name = "profil"
        verbose_name_plural = "profils"

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def profile_picture_url(self):
        # si l'utilisateur a uploadé une photo, on renvoie son URL
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        # sinon, on renvoie l'image par défaut stockée dans static
        return static('assets/img/profile.png')
    
 # Langues enseignées
class Language(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="nom")
    code = models.CharField(max_length=10, unique=True, verbose_name="code")
    description = models.TextField(blank=True, verbose_name="description")
    is_active = models.BooleanField(default=True, verbose_name="actif")
    
    class Meta:
        verbose_name = "langue"
        verbose_name_plural = "langues"
    
    def __str__(self):
        return self.name

# Étudiant
class Student(models.Model):
    
    STUDENT_STATUT= (
        ('actif', 'Actif'),
        ('pause', 'Pause'),
        ('terminé', 'Terminé'),
        ('abandon', 'Abandon'),
        ('attente', 'En attente'),
    )
    
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE,
        verbose_name="utilisateur"
    )
    matricule = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        verbose_name="matricule"
    )
    statuts = models.CharField(
        max_length=20, 
        choices=STUDENT_STATUT,
        verbose_name="statut"
    )
    languages = models.ManyToManyField(
        Language, 
        related_name='students',
        verbose_name="langues"
    )
    date_joined = models.DateField(
        default=timezone.now,
        verbose_name="date d'inscription"
    )
    total_hours_purchased = models.IntegerField(
        default=0,
        verbose_name="heures totales achetées"
    )
    total_hours_used = models.IntegerField(
        default=0,
        verbose_name="heures totales utilisées"
    )
    current_teachers =  models.ManyToManyField(
        'Teacher',
        blank=True,
        related_name='current_students',
        verbose_name="enseignants actuels"
    )
    objectif_formation = models.TextField(
        blank=True,
        verbose_name="objectif de formation"
    )

    class Meta:
        verbose_name = "étudiant"
        verbose_name_plural = "étudiants"

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
    STATUT_CHOICES = (
        ('actif', 'Actif'),
        ('disponible', 'Disponible'),
        ('conge', 'En congé'),
        ('plein', 'Plein'),
        ('inactif', 'Inactif'),
    )
     
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE,
        verbose_name="utilisateur"
    )
    speciality = models.CharField(
        max_length=100,
        verbose_name="spécialité"
    )
    statut = models.CharField(  max_length=20, 
        choices=STATUT_CHOICES,
        verbose_name="statut",
        default='disponible'
        )
    date_joined = models.DateField(
        default=timezone.now,
        verbose_name="date d'inscription"
    )
    languages = models.ManyToManyField(
        Language, 
        related_name='teachers',
        verbose_name="langues"
    )
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="taux horaire"
    )
    taux_remuneration = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=55.00,
        verbose_name="taux de rémunération (%)"
    )

    class Meta:
        verbose_name = "enseignant"
        verbose_name_plural = "enseignants"

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


# Emploi du temps
class Schedule(models.Model): 
    DAY_CHOICES = [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
         ('Dimanche', 'Dimanche'),
    ]

    day = models.CharField(
        max_length=10, 
        choices=DAY_CHOICES,
        verbose_name="jour"
    )
   
    language = models.ForeignKey(
        Language, 
        on_delete=models.CASCADE,
        verbose_name="languages"
    )
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE,  
        blank=True,
        verbose_name="étudiant"
    )
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
       
        blank=True,
        verbose_name="enseignant"
    )
    classroom = models.CharField(
        max_length=30, 
        blank=True, 
        null=True,
        verbose_name="salle de cours"
    )
    start_time = models.TimeField(
        verbose_name="heure de début"
    )
    end_time = models.TimeField(
        verbose_name="heure de fin"
    )
   
    is_active = models.BooleanField(
        default=True,
        verbose_name="actif"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour"
    )

    class Meta:
        ordering = ['day', 'start_time']
        unique_together = ['day', 'language', 'teacher', 'student' ,'start_time']
        verbose_name = "emploi du temps"
        verbose_name_plural = "emplois du temps"

    def __str__(self):
        return f"{self.language.name} - {self.day} ({self.start_time} - {self.end_time})"
    
  

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
    
    title = models.CharField(
        max_length=200,
        verbose_name="titre"
    )
    description = models.TextField(verbose_name="description")
    language = models.ForeignKey(
        Language, 
        on_delete=models.CASCADE,
        verbose_name="langue"
    )
    type = models.CharField(
        max_length=20, 
        choices=TYPES,
        verbose_name="type"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS, 
        default='draft',
        verbose_name="statut"
    )
    due_date = models.DateTimeField(verbose_name="date d'échéance")
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour"
    )
    
    class Meta:
        verbose_name = "devoir"
        verbose_name_plural = "devoirs"
    
    @property
    def is_late(self):
        return timezone.now() > self.due_date
    
    @property
    def submission_rate(self):
        total_students = self.language.students.count()
        if total_students > 0:
            submissions = self.submissions.count()
            return round((submissions / total_students) * 100, 2)
        return 0
    
    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment, 
        on_delete=models.CASCADE, 
        related_name='submissions',
        verbose_name="devoir"
    )
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE,
        verbose_name="étudiant"
    )
    file = models.FileField(
        upload_to='submissions/',
        verbose_name="fichier"
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de soumission"
    )
   
    feedback = models.TextField(
        null=True, 
        blank=True,
        verbose_name="feedback"
    )

    class Meta:
        unique_together = ['assignment', 'student']
        verbose_name = "soumission"
        verbose_name_plural = "soumissions"

    def __str__(self):
        return f"{self.student} - {self.assignment}"

# Séances de cours
class Session(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Prévue'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('rescheduled', 'Reportée'),
        ('absent', 'Absence')
    ]

    TYPE_SEANCE_CHOICES = [
        ('individuelle', 'Individuelle'),
        ('groupe', 'Groupe'),
    ]

    SCORE_CHOICES = [
        (1, '1 - Faible'),
        (2, '2 - Passable'),
        (3, '3 - Bien'),
        (4, '4 - Excellent'),
    ]

    VALIDATION_CHOICES = [
        ('en_attente', 'En attente'),
        ('validee', 'Validée'),
        ('refusee', 'Refusée'),
    ]

    # --- Identification ---
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="étudiant"
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="enseignant"
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        verbose_name="langue"
    )
    date = models.DateField(verbose_name="date")
    start_time = models.TimeField(verbose_name="heure de début")
    end_time = models.TimeField(verbose_name="heure de fin")
    duree_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="durée (minutes)"
    )
    type_seance = models.CharField(
        max_length=20,
        choices=TYPE_SEANCE_CHOICES,
        default='individuelle',
        verbose_name="type de séance"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name="statut"
    )
    meeting_link = models.URLField(
        blank=True,
        null=True,
        verbose_name="lien de réunion"
    )

    # --- Contenu pédagogique ---
    theme_cours = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="thème du cours"
    )
    comp_oral = models.BooleanField(default=False, verbose_name="Oral")
    comp_comprehension = models.BooleanField(default=False, verbose_name="Compréhension")
    comp_ecrit = models.BooleanField(default=False, verbose_name="Écrit")
    comp_grammaire = models.BooleanField(default=False, verbose_name="Grammaire")
    comp_vocabulaire = models.BooleanField(default=False, verbose_name="Vocabulaire")

    # --- Évaluation rapide ---
    participation = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        null=True,
        blank=True,
        verbose_name="participation (1-4)"
    )
    comprehension_score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        null=True,
        blank=True,
        verbose_name="compréhension (1-4)"
    )
    engagement = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        null=True,
        blank=True,
        verbose_name="engagement (1-4)"
    )

    # --- Analyse pédagogique ---
    difficultes = models.TextField(
        blank=True,
        verbose_name="difficultés rencontrées"
    )
    observations_formateur = models.TextField(
        blank=True,
        verbose_name="observations du formateur"
    )
    prochaine_etape = models.TextField(
        blank=True,
        verbose_name="prochaine étape pédagogique"
    )

    # --- Devoir ---
    devoir_donne = models.BooleanField(
        default=False,
        verbose_name="devoir donné"
    )
    description_devoir = models.TextField(
        blank=True,
        verbose_name="description du devoir"
    )

    # --- Validation fiche ---
    seance_realisee = models.BooleanField(
        default=False,
        verbose_name="séance réalisée"
    )
    fiche_completee = models.BooleanField(
        default=False,
        verbose_name="fiche complétée"
    )
    statut_validation = models.CharField(
        max_length=20,
        choices=VALIDATION_CHOICES,
        default='en_attente',
        verbose_name="statut de validation"
    )

    # --- Champs legacy ---
    notes = models.TextField(
        blank=True,
        verbose_name="notes"
    )
    feedback = models.TextField(
        blank=True,
        verbose_name="feedback"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour"
    )

    class Meta:
        ordering = ['-date', '-start_time']
        verbose_name = "séance"
        verbose_name_plural = "séances"

    @property
    def duration_hours(self):
        if self.duree_minutes:
            return self.duree_minutes / 60
        if self.start_time and self.end_time:
            start = datetime.combine(self.date, self.start_time)
            end = datetime.combine(self.date, self.end_time)
            duration = end - start
            return duration.total_seconds() / 3600
        return 0

    @property
    def competences_list(self):
        comps = []
        if self.comp_oral: comps.append("Oral")
        if self.comp_comprehension: comps.append("Compréhension")
        if self.comp_ecrit: comps.append("Écrit")
        if self.comp_grammaire: comps.append("Grammaire")
        if self.comp_vocabulaire: comps.append("Vocabulaire")
        return comps

    def __str__(self):
        return f"{self.student} - {self.language} - {self.date} ({self.get_status_display()})"

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
    
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='payments',
        verbose_name="étudiant"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="montant"
    )
    hours_purchased = models.IntegerField(verbose_name="heures achetées")
    hours_remaining = models.IntegerField(verbose_name="heures restantes")
    payment_type = models.CharField(
        max_length=20, 
        choices=PAYMENT_TYPES,
        verbose_name="type de paiement"
    )
    languages = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='payments_language', blank=True,)
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="statut"
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de paiement"
    )
    expiry_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="date d'expiration"
    )
    invoice_number = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        auto_created=True,
        verbose_name="numéro de facture"
    )
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
    
    def __str__(self):
        return f"{self.student} - {self.amount}MAD ({self.get_status_display()})"

# Certificats
class Certificate(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name="étudiant"
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        verbose_name="langue"
    )
    level = models.CharField(
        max_length=50,
        verbose_name="niveau"
    )
    issued_date = models.DateField(
        auto_now_add=True,
        verbose_name="date d'émission"
    )
    certificate_file = models.FileField(
        upload_to='certificates/',
        null=True,
        blank=True,
        verbose_name="fichier du certificat"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="actif"
    )
    # Nouveaux champs
    certificate_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name="ID du certificat"
    )
    duree_formation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="durée de formation"
    )
    competences_validees = models.TextField(
        blank=True,
        verbose_name="compétences validées"
    )
    appreciation_pedagogique = models.TextField(
        blank=True,
        verbose_name="appréciation pédagogique"
    )

    class Meta:
        ordering = ['-issued_date']
        verbose_name = "certificat"
        verbose_name_plural = "certificats"

    def __str__(self):
        return f"{self.student} - {self.language} - {self.level}"


@receiver(pre_save, sender=Certificate)
def generate_certificate_id(sender, instance, **kwargs):
    if not instance.certificate_id:
        year = timezone.now().year
        prefix = f"ORA-{year}-"
        last = Certificate.objects.filter(
            certificate_id__startswith=prefix
        ).order_by('-certificate_id').first()
        if last and last.certificate_id:
            match = re.search(r'(\d+)$', last.certificate_id)
            next_num = int(match.group(1)) + 1 if match else 1
        else:
            next_num = 1
        instance.certificate_id = f"{prefix}{next_num:03d}"

# Évaluations
class Evaluation(models.Model):
    EVALUATION_TYPES = [
        ('pronunciation', 'Prononciation'),
        ('grammar', 'Grammaire'),
        ('vocabulary', 'Vocabulaire'),
        ('fluency', 'Fluidité'),
        ('comprehension', 'Compréhension')
    ]
    
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='evaluations',
        verbose_name="étudiant"
    )
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='evaluations',
        verbose_name="enseignant"
    )
    language = models.ForeignKey(
        Language, 
        on_delete=models.CASCADE,
        verbose_name="langue"
    )
    evaluation_type = models.CharField(
        max_length=20, 
        choices=EVALUATION_TYPES,
        verbose_name="type d'évaluation"
    )
    score = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        verbose_name="score"
    )
    comments = models.TextField(
        blank=True,
        verbose_name="commentaires"
    )
    evaluation_date = models.DateField(
        auto_now_add=True,
        verbose_name="date d'évaluation"
    )
    
    class Meta:
        ordering = ['-evaluation_date']
        verbose_name = "évaluation"
        verbose_name_plural = "évaluations"
    
    def __str__(self):
        return f"{self.student} - {self.language} - {self.get_evaluation_type_display()}: {self.score}"

# Ressources pédagogiques
class Resource(models.Model):
    RESOURCE_TYPES = [
        ('document', 'Document'),
        ('link', 'Lien'),
        ('video', 'Vidéo'),
        ('other', 'Autre')
    ]
    
  
    
    title = models.CharField(
        max_length=200,
        verbose_name="titre"
    )
    description = models.TextField(
        blank=True,
        verbose_name="description"
    )
    file = models.FileField(
        upload_to='resources/%Y/%m/%d/', 
        null=True, 
        blank=True,
        verbose_name="fichier"
    )
    url = models.URLField(
        null=True, 
        blank=True,
        verbose_name="URL"
    )
    resource_type = models.CharField(
        max_length=20, 
        choices=RESOURCE_TYPES,
        verbose_name="type de ressource"
    )
    
    
    # Relation ManyToMany avec les étudiants
    students = models.ManyToManyField(
        'Student',
        blank=True,
        related_name='resources',
        verbose_name="étudiants ciblés"
    )
    
    # Langues (garder une seule relation ManyToMany)
    languages = models.ManyToManyField(
        'Language',
        blank=True,
        related_name='resources',
        verbose_name="langues concernées"
    )
    
    teachers = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='teachers_resources',
        verbose_name="enseignant responsable",
        blank=True
    )
    
    is_visible = models.BooleanField(
        default=True,
        verbose_name="visible"
    )
   
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="disponible jusqu'au"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "ressource pédagogique"
        verbose_name_plural = "ressources pédagogiques"

    def __str__(self):
        return f"{self.teachers.user.get_full_name()} - {self.title}"
    
    
    
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
    
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='requests',
        verbose_name="étudiant"
    )
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='received_requests', 
        blank=True,
        verbose_name="enseignant"
    )
    request_type = models.CharField(
        max_length=20, 
        choices=REQUEST_TYPES,
        verbose_name="type de demande"
    )
    subject = models.CharField(
        max_length=200,
        verbose_name="sujet"
    )
    description = models.TextField(verbose_name="description")
    attachment = models.FileField(
        upload_to='request_attachments/', 
        null=True, 
        blank=True,
        verbose_name="pièce jointe"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="statut"
    )
    response = models.TextField(
        blank=True, 
        null=True,
        verbose_name="réponse"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "demande"
        verbose_name_plural = "demandes"

    def __str__(self):
        return f"{self.student.user.username} - {self.subject} ({self.get_status_display()})"

# Notifications
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('session_reminder', 'Rappel de séance'),
        ('payment_due', 'Paiement dû'),
        ('certificate_ready', 'Certificat disponible'),
        ('evaluation_ready', 'Évaluation disponible'),
        ('system', 'Système')
    ]
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name="utilisateur"
    )
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES,
        verbose_name="type de notification"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="titre"
    )
    message = models.TextField(verbose_name="message")
    is_read = models.BooleanField(
        default=False,
        verbose_name="lu"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "notification"
        verbose_name_plural = "notifications"
    
    def __str__(self):
        return f"{self.user} - {self.title}"

# Commentaires étudiant sur enseignant
class Comment(models.Model):
    comment = models.TextField(
        blank=True, 
        null=True,
        verbose_name="commentaire"
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Note de 1 (mauvais) à 5 (excellent)",
        verbose_name="note"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="étudiant"
    )
    teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="enseignant"
    )
    language = models.ForeignKey(
        'Language',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="langue"
    )
    comment_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date du commentaire"
    )

    class Meta:
        unique_together = ('student', 'teacher', 'language')
        ordering = ['-comment_at']
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"

    def __str__(self):
        return f"{self.student} → {self.teacher} ({self.rating}/5)"
    
    
# Paiements formateurs
class PaiementFormateur(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('paye', 'Payé'),
        ('partiel', 'Partiel'),
    ]

    formateur = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='paiements_formateur',
        verbose_name="formateur"
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="montant (MAD)"
    )
    montant_calcule = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="montant calculé (55% CA)"
    )
    periode_debut = models.DateField(verbose_name="début de période")
    periode_fin = models.DateField(verbose_name="fin de période")
    commentaire = models.TextField(
        blank=True,
        verbose_name="commentaire"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="statut"
    )
    date_paiement = models.DateField(
        null=True,
        blank=True,
        verbose_name="date de paiement"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="date de mise à jour"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "paiement formateur"
        verbose_name_plural = "paiements formateurs"

    def __str__(self):
        return f"{self.formateur} — {self.montant}MAD ({self.get_statut_display()})"

    def calculer_montant(self):
        """Calcule 55% du CA généré par les séances validées sur la période."""
        from django.db.models import Sum
        sessions = Session.objects.filter(
            teacher=self.formateur,
            date__gte=self.periode_debut,
            date__lte=self.periode_fin,
            statut_validation='validee',
        )
        ca_total = 0
        for s in sessions:
            if s.student and s.duration_hours:
                paid = Payment.objects.filter(
                    student=s.student,
                    status='paid'
                ).aggregate(total=Sum('amount'))['total'] or 0
                hours_total = s.student.total_hours_purchased or 1
                ca_total += float(paid) * (s.duration_hours / hours_total)
        self.montant_calcule = round(ca_total * 0.55, 2)
        return self.montant_calcule


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'user_profile'):
        instance.user_profile.save()