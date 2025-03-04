import logging
import typing
import uuid

from django.db import models
from django.db.models import Manager
from simple_history.models import HistoricalRecords
from softdelete.models import SoftDeleteManager, SoftDeleteObject

from audit.related_object_type import RelatedObjectType

if typing.TYPE_CHECKING:
    from environments.models import Environment
    from projects.models import Project
    from users.models import FFAdminUser


logger = logging.getLogger(__name__)


class UUIDNaturalKeyManagerMixin:
    def get_by_natural_key(self, uuid_: str):
        logger.debug("Getting model %s by natural key", self.model.__name__)
        return self.get(uuid=uuid_)


class AbstractBaseExportableModelManager(UUIDNaturalKeyManagerMixin, Manager):
    pass


class AbstractBaseExportableModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    objects = AbstractBaseExportableModelManager()

    class Meta:
        abstract = True

    def natural_key(self):
        return (str(self.uuid),)


class SoftDeleteExportableManager(UUIDNaturalKeyManagerMixin, SoftDeleteManager):
    pass


class SoftDeleteExportableModel(SoftDeleteObject, AbstractBaseExportableModel):
    objects = SoftDeleteExportableManager()

    class Meta:
        abstract = True


class BaseHistoricalModel(models.Model):
    include_in_audit = True

    master_api_key = models.ForeignKey(
        "api_keys.MasterAPIKey", blank=True, null=True, on_delete=models.DO_NOTHING
    )

    class Meta:
        abstract = True


class _AbstractBaseAuditableModel(models.Model):
    """
    A base Model class that all models we want to be included in the audit log should inherit from.

    Some field descriptions:

     :history_record_class_path: the python class path to the HistoricalRecord model class.
        e.g. features.models.HistoricalFeature
     :related_object_type: a RelatedObjectType enum representing the related object type of the model.
        Note that this can be overridden by the `get_related_object_type` method in cases where it's
        different for certain scenarios.
    """

    history_record_class_path = None
    related_object_type = None

    class Meta:
        abstract = True

    def get_create_log_message(self, history_instance) -> typing.Optional[str]:
        """Override if audit log records should be written when model is created"""
        return None

    def get_update_log_message(self, history_instance) -> typing.Optional[str]:
        """Override if audit log records should be written when model is updated"""
        return None

    def get_delete_log_message(self, history_instance) -> typing.Optional[str]:
        """Override if audit log records should be written when model is deleted"""
        return None

    def get_environment_and_project(
        self,
    ) -> typing.Tuple[typing.Optional["Environment"], typing.Optional["Project"]]:
        environment, project = self._get_environment(), self._get_project()
        if environment or project:
            return environment, project
        else:
            raise RuntimeError(
                "One of _get_environment() or _get_project() must "
                "be implemented and return a non-null value"
            )

    def get_extra_audit_log_kwargs(self, history_instance) -> dict:
        """Add extra kwargs to the creation of the AuditLog record"""
        return {}

    def get_audit_log_author(self, history_instance) -> typing.Optional["FFAdminUser"]:
        """Override the AuditLog author (in cases where history_user isn't populated for example)"""
        return None

    def get_audit_log_related_object_id(self, history_instance) -> int:
        """Override the related object ID in cases where it shouldn't be self.id"""
        return self.id

    def get_audit_log_related_object_type(self, history_instance) -> RelatedObjectType:
        """
        Override the related object type to account for writing audit logs for related objects
        when certain events happen on this model.
        """
        return self.related_object_type

    def _get_environment(self) -> typing.Optional["Environment"]:
        """Return the related environment for this model."""
        return None

    def _get_project(self) -> typing.Optional["Project"]:
        """Return the related project for this model."""
        return None


def abstract_base_auditable_model_factory(
    historical_records_excluded_fields: typing.List[str] = None,
) -> typing.Type[_AbstractBaseAuditableModel]:
    class Base(_AbstractBaseAuditableModel):
        history = HistoricalRecords(
            bases=[BaseHistoricalModel],
            excluded_fields=historical_records_excluded_fields or [],
            inherit=True,
        )

        class Meta:
            abstract = True

    return Base
