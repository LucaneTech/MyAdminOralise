from django.utils import timezone
from django import forms
from dashboard.models import (
    Profile, CustomUser, Resource, Session, SessionSeries, Student, Language,
    Certificate, PaiementFormateur, Teacher, Payment,
    Evaluation, Request, Notification, Assignment, Comment,
)
from allauth.account.forms import LoginForm, SignupForm, ResetPasswordForm
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm

TW_INPUT = 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#26b2bd]/30 focus:border-[#26b2bd] transition'
TW_TEXTAREA = 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#26b2bd]/30 focus:border-[#26b2bd] transition resize-y'
TW_SELECT = 'w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#26b2bd]/30 focus:border-[#26b2bd] transition bg-white'
TW_FILE = 'block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-[#26b2bd]/10 file:text-[#26b2bd] hover:file:opacity-80'
TW_CHECKBOX = 'rounded border-gray-300 text-[#26b2bd] focus:ring-[#26b2bd]'

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [ 'profile_picture', 'address', 'city','country', 'number', 'about']
        widgets = {
            'about': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'profile_picture': 'Photo de profil',
            'address': 'Adresse',
            'city': 'Ville',
            'country': 'Pays',
            'number': 'Numéro',
            'about': 'À propos de moi'
        }
 

class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        #heritage of father class
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.fields['login'].widget = forms.TextInput(attrs={'placeholder': 'Entrez votre Email'})
        self.fields['password'].widget = forms.PasswordInput(attrs={'placeholder': 'Entrez votre mot de passe'})
        self.fields['remember'].widget = forms.CheckboxInput(attrs={'class': TW_CHECKBOX})

    def clean(self):
        cleaned_data = super(CustomLoginForm, self).clean()
        if cleaned_data is None:
            return cleaned_data

        login = cleaned_data.get('login')
        password = cleaned_data.get('password')

        if login and password:
            user = authenticate(username=login, password=password)
            if user is not None:
                if not user.is_active:
                    raise forms.ValidationError("This account is inactive.")
                if user.role not in ['admin', 'teacher','student', 'visitor']:
                    raise forms.ValidationError("Invalid user role.")
            else:
                raise forms.ValidationError("Invalid login credentials.")
        return cleaned_data

# End of CustomLoginForm



# Start of CustomSignupForm

class CustomSignupForm(SignupForm):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget = forms.TextInput(attrs={'placeholder': "Entrez votre nom d'utilisateur"})
        self.fields['email'].widget = forms.EmailInput(attrs={'placeholder': 'Entrez votre Email'})
        self.fields['role'] = forms.ChoiceField(choices=self.ROLE_CHOICES, widget=forms.Select(attrs={'class': TW_SELECT}))
        self.fields['password1'].widget = forms.PasswordInput(attrs={'placeholder': 'Mot de passe'})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'placeholder': 'Confirmer mot de passe'})

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.role = self.cleaned_data['role']
        user.save()
        return user
    
    
    #password reset form# forms.py
class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(CustomResetPasswordForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget = forms.EmailInput(attrs={'placeholder': 'Entrez votre Email', 'class': TW_INPUT})
        
  

class ResourceForm(forms.ModelForm):    
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'resource_type', 'file', 'url',
            'students', 'valid_until', 'is_visible'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': TW_INPUT,
                'placeholder': 'Titre de la ressource'
            }),
            'description': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 4,
                'placeholder': 'Description détaillée de la ressource...'
            }),
            'resource_type': forms.Select(attrs={
                'class': TW_SELECT
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': TW_FILE
            }),
            'url': forms.URLInput(attrs={
                'class': TW_INPUT,
                'placeholder': 'https://exemple.com'
            }),
            'students': forms.SelectMultiple(attrs={
                'class': TW_SELECT,
                'data-placeholder': 'Sélectionnez des étudiants...'
            }),
            'valid_until': forms.DateTimeInput(attrs={
                'class': TW_INPUT,
                'type': 'datetime-local'
            }),
            'is_visible': forms.CheckboxInput(attrs={
                'class': TW_CHECKBOX
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Personnaliser les querysets
        if self.teacher:
            self.fields['students'].queryset = Student.objects.filter(
                current_teachers=self.teacher
            )
        
        # Rendre file et url optionnels
        self.fields['file'].required = False
        self.fields['url'].required = False
        
        # Ajouter des classes CSS supplémentaires
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = TW_INPUT
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        url = cleaned_data.get('url')
        students = cleaned_data.get('students')
        
        # Validation fichier/URL
        if not file and not url:
            raise forms.ValidationError(
                "Vous devez fournir soit un fichier, soit une URL."
            )
        
        if file and url:
            raise forms.ValidationError(
                "Veuillez fournir soit un fichier, soit une URL, pas les deux."
            )
        
        # Validation de la date d'expiration
        valid_until = cleaned_data.get('valid_until')
        if valid_until and valid_until < timezone.now():
            raise forms.ValidationError(
                "La date d'expiration ne peut pas être dans le passé."
            )
        
        return cleaned_data


      
    
class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['students', 'language', 'date', 'start_time', 'end_time',
                  'type_seance', 'status', 'meeting_link', 'event_color']
        widgets = {
            'students': forms.SelectMultiple(attrs={'class': TW_SELECT, 'size': '5'}),
            'language': forms.Select(attrs={'class': TW_SELECT}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': TW_INPUT}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': TW_INPUT}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': TW_INPUT}),
            'type_seance': forms.Select(attrs={'class': TW_SELECT}),
            'status': forms.Select(attrs={'class': TW_SELECT}),
            'meeting_link': forms.URLInput(attrs={'class': TW_INPUT,
                                                   'placeholder': 'https://meet.google.com/...'}),
            'event_color': forms.TextInput(attrs={'type': 'color', 'class': TW_INPUT}),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        if self.teacher:
            self.fields['language'].queryset = self.teacher.languages.all()
            self.fields['students'].queryset = Student.objects.filter(
                current_teachers=self.teacher
            )
        else:
            self.fields['students'].queryset = Student.objects.all()


class FichePedagogiqueForm(forms.ModelForm):
    """Formulaire de saisie de la fiche pédagogique après une séance."""
    class Meta:
        model = Session
        fields = [
            'duree_minutes', 'type_seance', 'theme_cours',
            'comp_oral', 'comp_comprehension', 'comp_ecrit', 'comp_grammaire', 'comp_vocabulaire',
            'participation', 'comprehension_score', 'engagement',
            'difficultes', 'observations_formateur', 'prochaine_etape',
            'devoir_donne', 'description_devoir',
            'seance_realisee',
        ]
        widgets = {
            'duree_minutes': forms.NumberInput(attrs={'class': TW_INPUT, 'placeholder': 'Ex: 60'}),
            'type_seance': forms.Select(attrs={'class': TW_SELECT}),
            'theme_cours': forms.TextInput(attrs={'class': TW_INPUT, 'placeholder': 'Thème abordé'}),
            'participation': forms.Select(attrs={'class': TW_SELECT}),
            'comprehension_score': forms.Select(attrs={'class': TW_SELECT}),
            'engagement': forms.Select(attrs={'class': TW_SELECT}),
            'difficultes': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
            'observations_formateur': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
            'prochaine_etape': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
            'description_devoir': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 2}),
        }
        labels = {
            'duree_minutes': 'Durée (minutes)',
            'type_seance': 'Type de séance',
            'theme_cours': 'Thème du cours',
            'comp_oral': 'Oral',
            'comp_comprehension': 'Compréhension',
            'comp_ecrit': 'Écrit',
            'comp_grammaire': 'Grammaire',
            'comp_vocabulaire': 'Vocabulaire',
            'participation': 'Participation (1-4)',
            'comprehension_score': 'Compréhension (1-4)',
            'engagement': 'Engagement (1-4)',
            'difficultes': 'Difficultés rencontrées',
            'observations_formateur': 'Observations du formateur',
            'prochaine_etape': 'Prochaine étape pédagogique',
            'devoir_donne': 'Devoir donné',
            'description_devoir': 'Description du devoir',
            'seance_realisee': 'Séance réalisée',
        }


class CertificateForm(forms.ModelForm):
    """Formulaire admin pour créer/modifier un certificat."""
    class Meta:
        model = Certificate
        fields = [
            'student', 'language', 'level',
            'certificate_file', 'is_active',
            'duree_formation', 'competences_validees', 'appreciation_pedagogique',
        ]
        widgets = {
            'student': forms.Select(attrs={'class': TW_SELECT}),
            'language': forms.Select(attrs={'class': TW_SELECT}),
            'level': forms.TextInput(attrs={'class': TW_INPUT, 'placeholder': 'Ex: B2'}),
            'certificate_file': forms.ClearableFileInput(attrs={'class': TW_FILE}),
            'duree_formation': forms.TextInput(attrs={'class': TW_INPUT, 'placeholder': 'Ex: 5 mois'}),
            'competences_validees': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 4,
                'placeholder': 'Compréhension orale\nExpression orale\nInteraction'}),
            'appreciation_pedagogique': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
        }
        labels = {
            'student': 'Étudiant',
            'language': 'Langue',
            'level': 'Niveau',
            'certificate_file': 'Fichier PDF',
            'is_active': 'Actif',
            'duree_formation': 'Durée de formation',
            'competences_validees': 'Compétences validées (une par ligne)',
            'appreciation_pedagogique': 'Appréciation pédagogique',
        }


class PaiementFormateurForm(forms.ModelForm):
    """Formulaire admin pour créer un paiement formateur."""
    class Meta:
        model = PaiementFormateur
        fields = ['formateur', 'montant', 'periode_debut', 'periode_fin', 'commentaire', 'statut', 'date_paiement']
        widgets = {
            'formateur': forms.Select(attrs={'class': TW_SELECT}),
            'montant': forms.NumberInput(attrs={'class': TW_INPUT, 'step': '0.01'}),
            'periode_debut': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'periode_fin': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'commentaire': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
            'statut': forms.Select(attrs={'class': TW_SELECT}),
            'date_paiement': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
        }
        labels = {
            'formateur': 'Formateur',
            'montant': 'Montant (MAD)',
            'periode_debut': 'Début de période',
            'periode_fin': 'Fin de période',
            'commentaire': 'Commentaire',
            'statut': 'Statut',
            'date_paiement': 'Date de paiement',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['formateur'].queryset = Teacher.objects.filter(statut__in=['actif', 'disponible'])


# ─────────────────────────────────────────────────────────────
#  FORMULAIRES ADMIN — GESTION COMPLÈTE
# ─────────────────────────────────────────────────────────────

W = {'class': TW_INPUT}
WTA = {'class': TW_TEXTAREA, 'rows': 3}
WCB = {'class': TW_CHECKBOX}


class AdminUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput(attrs=W))
    password2 = forms.CharField(label='Confirmer le mot de passe', widget=forms.PasswordInput(attrs=W))

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs=W),
            'first_name': forms.TextInput(attrs=W),
            'last_name': forms.TextInput(attrs=W),
            'email': forms.EmailInput(attrs=W),
            'role': forms.Select(attrs=W),
            'is_active': forms.CheckboxInput(attrs=WCB),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs=W),
            'first_name': forms.TextInput(attrs=W),
            'last_name': forms.TextInput(attrs=W),
            'email': forms.EmailInput(attrs=W),
            'role': forms.Select(attrs=W),
            'is_active': forms.CheckboxInput(attrs=WCB),
        }


class AdminResetPasswordForm(forms.Form):
    password1 = forms.CharField(label='Nouveau mot de passe', widget=forms.PasswordInput(attrs=W))
    password2 = forms.CharField(label='Confirmer', widget=forms.PasswordInput(attrs=W))

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return p2


class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['statuts', 'languages', 'current_teachers', 'total_hours_purchased', 'total_hours_used', 'objectif_formation']
        widgets = {
            'statuts': forms.Select(attrs=W),
            'languages': forms.SelectMultiple(attrs=W),
            'current_teachers': forms.SelectMultiple(attrs=W),
            'total_hours_purchased': forms.NumberInput(attrs=W),
            'total_hours_used': forms.NumberInput(attrs=W),
            'objectif_formation': forms.Textarea(attrs=WTA),
        }


class TeacherAdminForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['speciality', 'statut', 'languages', 'hourly_rate', 'taux_remuneration']
        widgets = {
            'speciality': forms.TextInput(attrs=W),
            'statut': forms.Select(attrs=W),
            'languages': forms.SelectMultiple(attrs=W),
            'hourly_rate': forms.NumberInput(attrs={**W, 'step': '0.01'}),
            'taux_remuneration': forms.NumberInput(attrs={**W, 'step': '0.01'}),
        }


class LanguageForm(forms.ModelForm):
    class Meta:
        model = Language
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs=W),
            'code': forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs=WTA),
            'is_active': forms.CheckboxInput(attrs=WCB),
        }


class SessionAdminForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            'students', 'teacher', 'language', 'date', 'start_time', 'end_time',
            'duree_minutes', 'type_seance', 'status', 'meeting_link', 'event_color',
            'notes', 'feedback',
        ]
        widgets = {
            'students': forms.SelectMultiple(attrs=W),
            'teacher': forms.Select(attrs=W),
            'language': forms.Select(attrs=W),
            'date': forms.DateInput(attrs={**W, 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={**W, 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={**W, 'type': 'time'}),
            'duree_minutes': forms.NumberInput(attrs=W),
            'type_seance': forms.Select(attrs=W),
            'status': forms.Select(attrs=W),
            'meeting_link': forms.URLInput(attrs=W),
            'event_color': forms.TextInput(attrs={'type': 'color', **W}),
            'notes': forms.Textarea(attrs=WTA),
            'feedback': forms.Textarea(attrs=WTA),
        }


class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['student', 'amount', 'hours_purchased', 'hours_remaining', 'payment_type', 'languages', 'status', 'expiry_date']
        widgets = {
            'student': forms.Select(attrs=W),
            'amount': forms.NumberInput(attrs={**W, 'step': '0.01'}),
            'hours_purchased': forms.NumberInput(attrs=W),
            'hours_remaining': forms.NumberInput(attrs=W),
            'payment_type': forms.Select(attrs=W),
            'languages': forms.Select(attrs=W),
            'status': forms.Select(attrs=W),
            'expiry_date': forms.DateInput(attrs={**W, 'type': 'date'}),
        }


class EvaluationAdminForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['student', 'teacher', 'language', 'evaluation_type', 'score', 'comments']
        widgets = {
            'student': forms.Select(attrs=W),
            'teacher': forms.Select(attrs=W),
            'language': forms.Select(attrs=W),
            'evaluation_type': forms.Select(attrs=W),
            'score': forms.NumberInput(attrs={**W, 'step': '0.01', 'min': '0', 'max': '20'}),
            'comments': forms.Textarea(attrs=WTA),
        }


class ResourceAdminForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'description', 'resource_type', 'file', 'url', 'teachers', 'students', 'languages', 'is_visible', 'valid_until']
        widgets = {
            'title': forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs=WTA),
            'resource_type': forms.Select(attrs=W),
            'file': forms.ClearableFileInput(attrs={'class': TW_FILE}),
            'url': forms.URLInput(attrs=W),
            'teachers': forms.Select(attrs=W),
            'students': forms.SelectMultiple(attrs=W),
            'languages': forms.SelectMultiple(attrs=W),
            'is_visible': forms.CheckboxInput(attrs=WCB),
            'valid_until': forms.DateTimeInput(attrs={**W, 'type': 'datetime-local'}),
        }


class RequestAdminForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['status', 'response']
        widgets = {
            'status': forms.Select(attrs=W),
            'response': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 5}),
        }


class NotificationAdminForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['user', 'notification_type', 'title', 'message']
        widgets = {
            'user': forms.Select(attrs=W),
            'notification_type': forms.Select(attrs=W),
            'title': forms.TextInput(attrs=W),
            'message': forms.Textarea(attrs=WTA),
        }


class AssignmentAdminForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'language', 'type', 'status', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs=W),
            'description': forms.Textarea(attrs=WTA),
            'language': forms.Select(attrs=W),
            'type': forms.Select(attrs=W),
            'status': forms.Select(attrs=W),
            'due_date': forms.DateTimeInput(attrs={**W, 'type': 'datetime-local'}),
        }


class SessionSeriesAdminForm(forms.ModelForm):
    class Meta:
        model = SessionSeries
        fields = [
            'teacher', 'language', 'students',
            'day_of_week', 'start_time', 'end_time',
            'recurrence_start', 'recurrence_end',
            'type_seance', 'meeting_link', 'notes',
        ]
        widgets = {
            'teacher': forms.Select(attrs={'class': TW_SELECT}),
            'language': forms.Select(attrs={'class': TW_SELECT}),
            'students': forms.SelectMultiple(attrs={'class': TW_SELECT + ' h-32'}),
            'day_of_week': forms.Select(attrs={'class': TW_SELECT}),
            'start_time': forms.TimeInput(attrs={'class': TW_INPUT, 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': TW_INPUT, 'type': 'time'}),
            'recurrence_start': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'recurrence_end': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'type_seance': forms.Select(attrs={'class': TW_SELECT}),
            'meeting_link': forms.URLInput(attrs={'class': TW_INPUT}),
            'notes': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
        }


class SessionSeriesTeacherForm(forms.ModelForm):
    class Meta:
        model = SessionSeries
        fields = [
            'language', 'students',
            'day_of_week', 'start_time', 'end_time',
            'recurrence_start', 'recurrence_end',
            'type_seance', 'meeting_link', 'notes',
        ]
        widgets = {
            'language': forms.Select(attrs={'class': TW_SELECT}),
            'students': forms.SelectMultiple(attrs={'class': TW_SELECT + ' h-32'}),
            'day_of_week': forms.Select(attrs={'class': TW_SELECT}),
            'start_time': forms.TimeInput(attrs={'class': TW_INPUT, 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': TW_INPUT, 'type': 'time'}),
            'recurrence_start': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'recurrence_end': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'type_seance': forms.Select(attrs={'class': TW_SELECT}),
            'meeting_link': forms.URLInput(attrs={'class': TW_INPUT}),
            'notes': forms.Textarea(attrs={'class': TW_TEXTAREA, 'rows': 3}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            self.fields['language'].queryset = teacher.languages.all()
            self.fields['students'].queryset = Student.objects.filter(
                current_teachers=teacher
            ).select_related('user')