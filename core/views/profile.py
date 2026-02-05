from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect

from core.forms.profile_forms import UserEditForm, UserProfileEditForm
from core.models import UserProfile
from core.models.base_context import base_context


@login_required
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = UserProfileEditForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()

            messages.success(request, "Profile updated.")
            return redirect("core:profile")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = UserProfileEditForm(instance=profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "profile": profile,
        **base_context(request),
    }

    return render(request, "core/profile_edit.html", context)
