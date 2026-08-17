from django.contrib.admin.views.autocomplete import AutocompleteJsonView


class AvatarAutocompleteJsonView(AutocompleteJsonView):
    """
    Adds an "avatar" key (uploaded image URL, or "" if none) to each result
    when the field being searched targets the User model, so the Select2
    dropdown JS (static/admin/js/user-autocomplete.js) can render a picture
    next to the name. Every other autocomplete (Category, Product, ...) goes
    through unchanged since `serialize_result` only special-cases User.
    """

    def serialize_result(self, obj, to_field_name):
        result = super().serialize_result(obj, to_field_name)
        if self.model_admin.model._meta.label == "users.User":
            avatar = obj.avatar.url if obj.avatar else obj.avatar_url
            result["avatar"] = avatar or ""
            result["initial"] = (obj.get_full_name() or obj.get_username() or "?")[0].upper()
        return result
