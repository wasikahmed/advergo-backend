from django import forms
from django.contrib import admin, messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from unfold.widgets import UnfoldAdminImageFieldWidget, UnfoldAdminTextInputWidget

from .models import User


class ProfileForm(forms.ModelForm):
    """
    Deliberately narrow: only the fields a staff member should be able to
    change about themselves. Nothing here can touch is_staff/is_superuser/
    groups/permissions -- that's UserAdmin's job, gated by the
    users.change_user permission most staff don't have.
    """

    class Meta:
        model = User
        fields = ["full_name", "phone", "avatar"]
        widgets = {
            "full_name": UnfoldAdminTextInputWidget(),
            "phone": UnfoldAdminTextInputWidget(),
            "avatar": UnfoldAdminImageFieldWidget(),
        }


@login_required
def my_profile(request):
    if not request.user.is_staff:
        return redirect("admin:index")

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("admin-profile")
    else:
        form = ProfileForm(instance=request.user)

    context = {"form": form, "title": "My profile", **admin.site.each_context(request)}
    return render(request, "admin_profile.html", context)
