from django import forms
from dashboard.models import Profile, CustomUser
from django import forms
from allauth.account.forms import LoginForm, SignupForm,ResetPasswordForm
from django.contrib.auth import authenticate

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [ 'profile_picture', 'city', 'country', 'address', 'about']
        widgets = {
            'about': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'profile_picture': 'Photo de profil',
            'city': 'Ville',
            'country': 'Pays',
            'address': 'Adresse',
            'about': 'À propos de moi'
        }
 

class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.fields['login'].widget = forms.TextInput(attrs={'placeholder': 'Entrez votre Email'})
        self.fields['password'].widget = forms.PasswordInput(attrs={'placeholder': 'Entrez votre mot de passe'})
        # self.fields['remember'].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})

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
        ('visitor', 'Visitor'),
       
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
        self.fields['email'].widget = forms.EmailInput(attrs={'placeholder': 'Entrez votre Email'})
        

    
       