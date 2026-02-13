from time import timezone
from django import forms
from dashboard.models import Profile, CustomUser, Resource, Session, Student, Language
from django import forms
from allauth.account.forms import LoginForm, SignupForm,ResetPasswordForm
from django.contrib.auth import authenticate

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
        self.fields['remember'].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})

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
        self.fields['role'] = forms.ChoiceField(choices=self.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'dropdown'}))
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
        self.fields['email'].widget = forms.EmailInput(attrs={'placeholder': 'Entrez votre Email', 'class': 'custom-input'})
        
  

class ResourceForm(forms.ModelForm):    
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'resource_type', 'file', 'url',
            'students', 'teachers', 'languages', 'valid_until', 'is_visible'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de la ressource'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description détaillée de la ressource...'
            }),
            'resource_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control-file'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://exemple.com'
            }),
            'students': forms.SelectMultiple(attrs={
                'class': 'form-control select2-multiple',
                'data-placeholder': 'Sélectionnez des étudiants...'
            }),
            'teachers':forms.TextInput(),
            'languages': forms.SelectMultiple(attrs={
                'class': 'form-control select2-multiple',
                'data-placeholder': 'Sélectionnez des langues...'
            }),
            'valid_until': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_visible': forms.CheckboxInput(attrs={
                'class': 'custom-control-input'
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
            # Limiter les langues aux langues de l'enseignant si nécessaire
            if hasattr(self.teacher, 'languages'):
                self.fields['languages'].queryset = self.teacher.languages.all()
        
        # Rendre file et url optionnels
        self.fields['file'].required = False
        self.fields['url'].required = False
        
        # Ajouter des classes CSS supplémentaires
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
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
        fields = ['language', 'date', 'start_time', 'end_time', 'status', 'student', 'meeting_link']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'Sélectionnez une date'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time', 
                'class': 'form-control',
                'placeholder': 'Heure de début'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control', 
                'placeholder': 'Heure de fin'
            }),
            'language': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'student': forms.Select(attrs={
                'class': 'form-control'
            }),
            'meeting_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://meet.google.com/...'
            }),
        }
    


def __init__(self, *args, **kwargs):
        # Récupérer l'enseignant pour filtrer les étudiants
        self.teacher = kwargs.pop('teacher', None)
        self.session_instance = kwargs.get('instance', None)
        super(SessionForm, self).__init__(*args, **kwargs)
        
        if self.teacher:
            # Filtrer les langues disponibles pour cet enseignant
            self.fields['language'].queryset = self.teacher.languages.all()
            
            # Filtrer les étudiants (selon votre logique métier)
            # Option 1: Tous les étudiants
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['student'].queryset = User.objects.filter(role='student')