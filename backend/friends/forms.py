from django import forms
from users.models import CustomUser

class UserSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search for users by username or email'})
    )