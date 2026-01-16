from django import forms
from .models import Conversation
from users.models import CustomUser

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

class CreateGroupForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=True)
    participants = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = Conversation
        fields = ['name']
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CreateGroupForm, self).__init__(*args, **kwargs)
        
        if user:
            # Only show friends as potential participants
            from friends.models import FriendRequest
            from django.db.models import Q
            
            friends_1 = FriendRequest.objects.filter(
                sender=user,
                status='accepted'
            ).values_list('receiver', flat=True)
            
            friends_2 = FriendRequest.objects.filter(
                receiver=user,
                status='accepted'
            ).values_list('sender', flat=True)
            
            friends = CustomUser.objects.filter(Q(id__in=friends_1) | Q(id__in=friends_2))
            
            # Only allow verified users for group chats
            verified_friends = friends.filter(is_verified=True)
            
            self.fields['participants'].queryset = verified_friends