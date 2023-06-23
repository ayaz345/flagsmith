import typing

from django.db.models import Q
from rest_framework import serializers

from features.serializers import FeatureStateSerializerFull
from integrations.common.serializers import (
    BaseEnvironmentIntegrationModelSerializer,
)
from segments.models import Segment

from .models import WebhookConfiguration


class WebhookConfigurationSerializer(BaseEnvironmentIntegrationModelSerializer):
    class Meta:
        model = WebhookConfiguration
        fields = ("id", "url", "secret")


class SegmentSerializer(serializers.ModelSerializer):
    member = serializers.SerializerMethodField()

    class Meta:
        model = Segment
        fields = ("id", "name", "member")

    def get_member(self, obj):
        return obj.does_identity_match(identity=self.context.get("identity"))


class IntegrationFeatureStateSerializer(FeatureStateSerializerFull):
    def to_representation(self, instance):
        return_value = super().to_representation(instance)
        if value := return_value["feature_state_value"]:
            return_value["percentage_allocation"] = self.get_percentage_allocation(
                value, instance
            )
        return return_value

    def get_percentage_allocation(self, value, instance) -> typing.Optional[float]:
        value_filter = {
            str: Q(multivariate_feature_option__string_value=value),
            int: Q(multivariate_feature_option__integer_value=value),
            bool: Q(multivariate_feature_option__boolean_value=value),
        }.get(type(value))
        if mv_fs := instance.multivariate_feature_state_values.filter(
            value_filter
        ).first():
            return mv_fs.percentage_allocation
