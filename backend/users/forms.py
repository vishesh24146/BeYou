from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django import forms
from .models import CustomUser, Report
from captcha.fields import CaptchaField

class UserReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'additional_details', 'screenshot']
        widgets = {
            'reason': forms.Select(choices=[
                ('harassment', 'Harassment or Bullying'),
                ('spam', 'Spam or Scam'),
                ('impersonation', 'Fake Account/Impersonation'),
                ('inappropriate', 'Inappropriate Content'),
                ('hate_speech', 'Hate Speech'),
                ('other', 'Other (please specify)'),
            ], attrs={'class': 'form-select'}),
            'additional_details': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'screenshot': forms.FileInput(attrs={'class': 'form-control'}),
        }

class MessageReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'additional_details', 'screenshot']
        widgets = {
            'reason': forms.Select(choices=[
                ('harassment', 'Harassment or Bullying'),
                ('spam', 'Spam or Scam'),
                ('inappropriate', 'Inappropriate Content'),
                ('hate_speech', 'Hate Speech'),
                ('threats', 'Threats or Violence'),
                ('other', 'Other (please specify)'),
            ], attrs={'class': 'form-select'}),
            'additional_details': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'screenshot': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ItemReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'additional_details', 'screenshot']
        widgets = {
            'reason': forms.Select(choices=[
                ('counterfeit', 'Counterfeit or Fake'),
                ('prohibited', 'Prohibited Item'),
                ('misleading', 'Misleading Description'),
                ('inappropriate', 'Inappropriate Content'),
                ('scam', 'Scam or Fraud'),
                ('other', 'Other (please specify)'),
            ], attrs={'class': 'form-select'}),
            'additional_details': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'screenshot': forms.FileInput(attrs={'class': 'form-control'}),
        }

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )


class PasswordResetVerifyForm(forms.Form):
    token = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '6-digit code from authenticator app',
            'maxlength': '6', 
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        })
    )

class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False
    )
    password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False
    )
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

class VerificationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['id_document', 'verification_reason']
        widgets = {
            'verification_reason': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control'
            }),
            'id_document': forms.FileInput(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
        }


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=15)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
###############################################

# class RegisterWithCaptchaForm(UserRegisterForm):
#     captcha = CaptchaField()

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['captcha'].widget.attrs.update({'class': 'form-control'})


from django.core.exceptions import ValidationError

class RegisterWithCaptchaForm(UserRegisterForm):
    captcha = CaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['captcha'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email





# class AdminLoginWithCaptchaForm(AuthenticationForm):
#     captcha = CaptchaField()

#######################################################



class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture', 'bio']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell others a bit about yourself'}),
        }

class MessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Type your message here...'}),
        required=False
    )
    media_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*,video/*'})
    )
    media_type = forms.ChoiceField(
        choices=[('none', 'None'), ('image', 'Image'), ('video', 'Video')],
        required=False,
        widget=forms.HiddenInput()
    )
    enable_e2e = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        media_file = cleaned_data.get('media_file')
        
        if not content and not media_file:
            raise forms.ValidationError("Either message content or media file is required.")
        
        # Auto-detect media type if file is provided
        if media_file:
            if hasattr(media_file, 'content_type'):
                if 'image' in media_file.content_type:
                    cleaned_data['media_type'] = 'image'
                elif 'video' in media_file.content_type:
                    cleaned_data['media_type'] = 'video'
                else:
                    raise forms.ValidationError("Unsupported file type. Only images and videos are allowed.")
            else:
                # Fallback to checking file extension
                filename = media_file.name.lower()
                if filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    cleaned_data['media_type'] = 'image'
                elif filename.endswith(('.mp4', '.mov', '.avi', '.webm')):
                    cleaned_data['media_type'] = 'video'
                else:
                    raise forms.ValidationError("Unsupported file type. Only images and videos are allowed.")
        
        return cleaned_data



############


class LoginWithCaptchaForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(max_length=150,widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    captcha = CaptchaField()