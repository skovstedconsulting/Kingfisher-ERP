"""Admin mixins to keep admin code simple and consistent."""

from django.contrib import admin
from core.permissions import assign_object_perms_to_user, assign_object_perms_to_entity_admins

class EntityScopedAdminMixin:
    """Mixin: after save, assign guardian permissions for visibility.

    This avoids relying on signals (signals don't know the request.user).
    """

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # If the object is entity-scoped, assign perms to current user and entity admins.
        entity = getattr(obj, "entity", None)
        if entity is not None:
            assign_object_perms_to_user(request.user, obj)
            assign_object_perms_to_entity_admins(entity, obj)

    def get_queryset(self, request):
        """Restrict queryset to objects the user has permission to view.

        Guardian provides get_objects_for_user, but to keep dependencies light in admin,
        we use the standard guarded admin pattern:
        - If superuser => see all
        - Else => filter by user's entity (simple, readable baseline)
        Later you can replace with guardian.shortcuts.get_objects_for_user for true object-level filtering.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        profile = getattr(request.user, "profile", None)
        if not profile:
            return qs.none()
        # baseline: entity filter
        if hasattr(qs.model, "entity_id"):
            return qs.filter(entity=profile.entity)
        return qs
