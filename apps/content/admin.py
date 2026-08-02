from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    Achievement,
    BankAccount,
    Banner,
    ClientLogo,
    CompanyInfo,
    GalleryCategory,
    GalleryItem,
    MobileBankingAgent,
    OfficialDocument,
    ProcessStep,
    Stat,
    TeamMember,
)


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = [
            "title",
            "subtitle",
            "image",
            "cta_label",
            "cta_href",
            "is_active",
            "priority",
            "featured_from",
            "featured_to",
        ]
        widgets = {"title": forms.Textarea(attrs={"rows": 2})}


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    form = BannerForm
    list_display = ["title", "is_active", "priority", "featured_from", "featured_to"]
    list_filter = ["is_active"]
    search_fields = ["title", "subtitle"]


@admin.register(Stat)
class StatAdmin(ModelAdmin):
    list_display = ["label", "value", "order"]
    ordering = ["order"]


@admin.register(Achievement)
class AchievementAdmin(ModelAdmin):
    list_display = ["title", "year", "issuing_body", "order"]
    ordering = ["order"]


@admin.register(ClientLogo)
class ClientLogoAdmin(ModelAdmin):
    list_display = ["name", "logo_image", "logo_url", "order"]
    search_fields = ["name"]
    ordering = ["order", "name"]


@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ["name", "role", "is_leadership", "order"]
    list_filter = ["is_leadership"]
    search_fields = ["name", "role"]
    ordering = ["order", "name"]


@admin.register(BankAccount)
class BankAccountAdmin(ModelAdmin):
    list_display = ["bank_name", "account_number", "swift_code", "order"]
    search_fields = ["bank_name", "account_number"]
    ordering = ["order", "bank_name"]


@admin.register(MobileBankingAgent)
class MobileBankingAgentAdmin(ModelAdmin):
    list_display = ["provider", "agent_number", "label", "order"]
    ordering = ["order", "provider"]


@admin.register(OfficialDocument)
class OfficialDocumentAdmin(ModelAdmin):
    """Staff-login-gated by Django admin; deliberately no public API for this model."""

    list_display = ["doc_type", "reference_number", "issue_date"]
    ordering = ["doc_type"]


@admin.register(ProcessStep)
class ProcessStepAdmin(ModelAdmin):
    list_display = ["number", "title", "order"]
    ordering = ["order"]


@admin.register(GalleryCategory)
class GalleryCategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "icon", "order"]
    ordering = ["order", "name"]
    search_fields = ["name", "slug"]


@admin.register(GalleryItem)
class GalleryItemAdmin(ModelAdmin):
    list_display = ["label", "category", "order"]
    list_filter = ["category"]
    search_fields = ["label", "description"]
    ordering = ["order"]
    autocomplete_fields = ["category"]


@admin.register(CompanyInfo)
class CompanyInfoAdmin(ModelAdmin):
    list_display = ["name", "phone", "email"]

    def has_add_permission(self, request):
        # Singleton -- only ever one row, created lazily by the API/seed script.
        return not CompanyInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
