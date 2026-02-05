from core.models.base_context import base_context

def base_context_processor(request):
    return base_context(request)