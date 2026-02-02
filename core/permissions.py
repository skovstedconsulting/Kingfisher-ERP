"""Guardian helpers for simple 'entity visibility'.

Goal:
- When an object is created/edited from admin, assign object-level permissions to:
  * the current user
  * optionally all entity admins (UserProfile.is_entity_admin=True)

We keep this explicit and readable. No magic signal that tries to infer the user.
"""

from guardian.shortcuts import assign_perm
from django.contrib.auth import get_user_model

from core.models import UserProfile

DEFAULT_PERMS = ("view", "change", "delete")

def assign_object_perms_to_user(user, obj, perms=DEFAULT_PERMS):
    """Assign view/change/delete perms for obj to a user."""
    if not user or not user.is_authenticated:
        return
    app_label = obj._meta.app_label
    model_name = obj._meta.model_name
    for p in perms:
        assign_perm(f"{app_label}.{p}_{model_name}", user, obj)

def assign_object_perms_to_entity_admins(entity, obj, perms=DEFAULT_PERMS):
    """Assign perms for obj to all users marked as entity admin."""
    qs = UserProfile.objects.filter(entity=entity, is_entity_admin=True).select_related("user")
    for prof in qs:
        assign_object_perms_to_user(prof.user, obj, perms=perms)
