from django import forms
from django.contrib.auth import get_user_model

from core.models import UserProfile

User = get_user_model()


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class UserProfileEditForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["image_url", "address"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 4}),
        }
