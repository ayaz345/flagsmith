from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from drf_yasg2.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import (
    METADATA_SUPPORTED_MODELS,
    SUPPORTED_REQUIREMENTS_MAPPING,
    MetadataField,
    MetadataModelField,
)
from .permissions import (
    MetadataFieldPermissions,
    MetadataModelFieldPermissions,
)
from .serializers import (
    ContentTypeSerializer,
    MetadataFieldQuerySerializer,
    MetadataFieldSerializer,
    MetadataModelFieldQuerySerializer,
    MetaDataModelFieldSerializer,
    SupportedRequiredForModelQuerySerializer,
)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(query_serializer=MetadataFieldQuerySerializer),
)
class MetadataFieldViewSet(viewsets.ModelViewSet):
    permission_classes = [MetadataFieldPermissions]
    serializer_class = MetadataFieldSerializer

    def get_queryset(self):
        queryset = MetadataField.objects.filter(organisation__users=self.request.user)
        if self.action == "list":
            serializer = MetadataFieldQuerySerializer(data=self.request.query_params)
            serializer.is_valid(raise_exception=True)
            organisation_id = serializer.validated_data["organisation"]

            if organisation_id is None:
                raise ValidationError("organisation parameter is required")
            queryset = queryset.filter(organisation__id=organisation_id)

        return queryset


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(query_serializer=MetadataModelFieldQuerySerializer),
)
class MetaDataModelFieldViewSet(viewsets.ModelViewSet):
    permission_classes = [MetadataModelFieldPermissions]
    serializer_class = MetaDataModelFieldSerializer

    def get_queryset(self):
        queryset = MetadataModelField.objects.filter(
            field__organisation_id=self.kwargs.get("organisation_pk")
        )
        serializer = MetadataModelFieldQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        if content_type := serializer.validated_data.get("content_type"):
            queryset = queryset.filter(content_type__id=content_type)

        return queryset

    @swagger_auto_schema(
        method="GET", responses={200: ContentTypeSerializer(many=True)}
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="supported-content-types",
    )
    def supported_content_types(self, request, organisation_pk=None):
        qs = ContentType.objects.filter(model__in=METADATA_SUPPORTED_MODELS)
        serializer = ContentTypeSerializer(qs, many=True)

        return Response(serializer.data)

    @swagger_auto_schema(
        method="GET",
        responses={200: ContentTypeSerializer(many=True)},
        query_serializer=SupportedRequiredForModelQuerySerializer,
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="supported-required-for-models",
    )
    def supported_required_for_models(self, request, organisation_pk=None):
        serializer = SupportedRequiredForModelQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        qs = ContentType.objects.filter(
            model__in=SUPPORTED_REQUIREMENTS_MAPPING.get(
                serializer.data["model_name"], {}
            ).keys()
        )
        serializer = ContentTypeSerializer(qs, many=True)

        return Response(serializer.data)
