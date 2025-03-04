from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from rest_framework import serializers

from organisations.models import Organisation
from projects.models import Project
from util.drf_writable_nested.serializers import (
    DeleteBeforeUpdateWritableNestedModelSerializer,
)

from .models import (
    SUPPORTED_REQUIREMENTS_MAPPING,
    Metadata,
    MetadataField,
    MetadataModelField,
    MetadataModelFieldRequirement,
)


class MetadataFieldQuerySerializer(serializers.Serializer):
    organisation = serializers.IntegerField(
        required=True, help_text="Organisation ID to filter by"
    )


class SupportedRequiredForModelQuerySerializer(serializers.Serializer):
    model_name = serializers.CharField(required=True)


class MetadataFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetadataField
        fields = ("id", "name", "type", "description", "organisation")


class MetadataModelFieldQuerySerializer(serializers.Serializer):
    content_type = serializers.IntegerField(
        required=False, help_text="Content type of the model to filter by."
    )


class MetadataModelFieldRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetadataModelFieldRequirement
        fields = ("content_type", "object_id")


class MetaDataModelFieldSerializer(DeleteBeforeUpdateWritableNestedModelSerializer):
    is_required_for = MetadataModelFieldRequirementSerializer(many=True, required=False)

    class Meta:
        model = MetadataModelField
        fields = ("id", "field", "content_type", "is_required_for")

    def validate(self, data):
        data = super().validate(data)
        for requirement in data.get("is_required_for", []):
            try:
                get_org_id_func = SUPPORTED_REQUIREMENTS_MAPPING[
                    data["content_type"].model
                ][requirement["content_type"].model]
            except KeyError:
                raise serializers.ValidationError(
                    f'Invalid requirement for model {data["content_type"].model}'
                )

            if (
                get_org_id_func(requirement["object_id"])
                != data["field"].organisation_id
            ):
                raise serializers.ValidationError(
                    "The requirement organisation does not match the field organisation"
                )
        return data


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ("id", "app_label", "model")


class MetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metadata
        fields = ("id", "model_field", "field_value")

    def validate(self, data):
        data = super().validate(data)
        if not data["model_field"].field.is_field_value_valid(data["field_value"]):
            raise serializers.ValidationError(
                f"Invalid value for field {data['model_field'].field.name}"
            )

        return data


class SerializerWithMetadata(serializers.BaseSerializer):
    def get_organisation_from_validated_data(self, validated_data) -> Organisation:
        raise NotImplementedError()

    def get_project_from_validated_data(self, validated_data) -> Project:
        raise NotImplementedError()

    def get_required_for_object(
        self, requirement: MetadataModelFieldRequirement, data: dict
    ) -> Model:
        model_name = requirement.content_type.model
        try:
            return getattr(self, f"get_{model_name}_from_validated_data")(data)
        except AttributeError:
            raise ValueError(
                f"`get_{model_name}_from_validated_data` method does not exist"
            )

    def validate_required_metadata(self, data):
        metadata = data.get("metadata", [])

        content_type = ContentType.objects.get_for_model(self.Meta.model)

        organisation = self.get_organisation_from_validated_data(data)

        requirements = MetadataModelFieldRequirement.objects.filter(
            model_field__content_type=content_type,
            model_field__field__organisation=organisation,
        )

        for requirement in requirements:
            required_for = self.get_required_for_object(requirement, data)
            if all(
                field["model_field"] != requirement.model_field
                for field in metadata
            ):
                if required_for.id == requirement.object_id:
                    raise serializers.ValidationError(
                        {
                            "metadata": f"Missing required metadata field: {requirement.model_field.field.name}"
                        }
                    )

    def validate(self, data):
        data = super().validate(data)
        self.validate_required_metadata(data)
        return data
