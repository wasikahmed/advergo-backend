import pytest
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType

from apps.activity.models import ActivityLog
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_log_entry_is_mirrored_into_activity_log():
    actor = UserFactory(email="mirroractor@example.com", is_staff=True)
    target = UserFactory(email="mirrortarget@example.com")

    LogEntry.objects.log_actions(
        actor.pk, [target], ADDITION, change_message="Added.", single_object=True
    )

    entry = ActivityLog.objects.get()
    assert entry.actor == actor
    assert entry.verb == "created"
    assert entry.object_repr == str(target)
    assert entry.content_type == ContentType.objects.get_for_model(target)
    assert entry.object_id == str(target.pk)
