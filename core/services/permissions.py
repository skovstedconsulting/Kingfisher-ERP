from guardian.shortcuts import assign_perm

def assign_entity_object_perms(user, obj):
    """Assign basic object permissions to a user for an entity-scoped object.

    Philosophy:
    - Simple, explicit, boring.
    - Called from admin save_model or signals.
    """
    model = obj.__class__._meta.model_name
    app = obj.__class__._meta.app_label

    assign_perm(f"{app}.view_{model}", user, obj)
    assign_perm(f"{app}.change_{model}", user, obj)
