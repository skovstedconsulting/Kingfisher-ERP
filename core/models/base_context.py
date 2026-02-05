from core.models import Menu

def base_context(request):
    if not request.user.is_authenticated:
        return {}

    return {
        "menus": Menu.objects.filter(
            active=True,
            parent__isnull=True,
        ).prefetch_related("children")
    }
