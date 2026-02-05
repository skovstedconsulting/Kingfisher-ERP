from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.models import Menu
from core.forms import MenuForm
from core.models.base_context import base_context
from django.contrib import messages

@login_required
def menu_edit(request, pk=None):
    menu = get_object_or_404(Menu, pk=pk) if pk else None

    if request.method == "POST":
        form = MenuForm(request.POST, instance=menu)
        if form.is_valid():
            form.save()
            return redirect("core:menu-edit")
    else:
        form = MenuForm(instance=menu)

    all_menus = Menu.objects.select_related("parent").order_by("parent_id", "sort_order", "menu")

    return render(request, "core/menu_edit.html", {
        "form": form,
        "editing": menu,
        "all_menus": all_menus,
        **base_context(request),
    })


@require_POST
@login_required
def menu_delete(request, pk):
    menu = get_object_or_404(Menu, pk=pk)
    menu.delete()
    messages.success(request, f"Menu item deleted")
    return redirect("core:menu-edit")
