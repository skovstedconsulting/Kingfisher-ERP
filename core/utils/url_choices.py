from django.urls import get_resolver, URLPattern, URLResolver, reverse
from django.urls.exceptions import NoReverseMatch

def _walk(patterns, namespace_prefix=""):
    for p in patterns:
        if isinstance(p, URLPattern) and p.name:
            full_name = f"{namespace_prefix}{p.name}" if namespace_prefix else p.name
            yield full_name
        elif isinstance(p, URLResolver):
            ns = p.namespace
            new_prefix = f"{namespace_prefix}{ns}:" if (namespace_prefix and ns) else (f"{ns}:" if ns else namespace_prefix)
            yield from _walk(p.url_patterns, new_prefix)

def discover_named_urls():
    choices = [("", "— select —")]
    seen = set()

    for full_name in _walk(get_resolver().url_patterns):
        if full_name in seen:
            continue
        try:
            path = reverse(full_name)          # e.g. "/menus/"
        except NoReverseMatch:
            continue
        seen.add(full_name)
        choices.append((path, f"{full_name}  →  {path}"))  # ✅ value is path

    return sorted(choices, key=lambda x: x[1])
