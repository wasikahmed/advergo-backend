from django.contrib import admin
from django.contrib.auth import views as auth_views

from .admin_forms import AdminPasswordResetForm, AdminSetPasswordForm


class AdminContextMixin:
    """
    Merges in everything AdminSite.each_context() provides (site_title,
    site_header, and -- critically -- the `colors` context that renders the
    :root{--color-base-50: ...} CSS custom properties every Unfold utility
    class depends on). Django's generic auth views never call this, since
    they aren't part of AdminSite; without it every Unfold class resolves to
    nothing and the page looks completely unstyled.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        return context


class AdminPasswordResetView(AdminContextMixin, auth_views.PasswordResetView):
    form_class = AdminPasswordResetForm


class AdminPasswordResetDoneView(AdminContextMixin, auth_views.PasswordResetDoneView):
    pass


class AdminPasswordResetConfirmView(AdminContextMixin, auth_views.PasswordResetConfirmView):
    form_class = AdminSetPasswordForm


class AdminPasswordResetCompleteView(AdminContextMixin, auth_views.PasswordResetCompleteView):
    pass
