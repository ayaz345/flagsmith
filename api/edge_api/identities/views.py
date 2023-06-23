import base64
import json
import typing

import marshmallow
from boto3.dynamodb.conditions import Key
from django.utils.decorators import method_decorator
from drf_yasg2.utils import swagger_auto_schema
from flag_engine.api.schemas import APITraitSchema
from flag_engine.identities.builders import (
    build_identity_dict,
    build_identity_model,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from app.pagination import (
    EdgeIdentityPagination,
    EdgeIdentityPaginationInspector,
)
from edge_api.identities.serializers import (
    EdgeIdentityFeatureStateSerializer,
    EdgeIdentityFsQueryparamSerializer,
    EdgeIdentityIdentifierSerializer,
    EdgeIdentitySerializer,
    EdgeIdentityTraitsSerializer,
    EdgeIdentityWithIdentifierFeatureStateDeleteRequestBody,
    EdgeIdentityWithIdentifierFeatureStateRequestBody,
)
from environments.identities.serializers import (
    IdentityAllFeatureStatesSerializer,
)
from environments.models import Environment
from environments.permissions.constants import (
    MANAGE_IDENTITIES,
    VIEW_IDENTITIES,
)
from environments.permissions.permissions import NestedEnvironmentPermissions
from features.models import FeatureState
from features.permissions import IdentityFeatureStatePermissions
from projects.exceptions import DynamoNotEnabledError

from .exceptions import TraitPersistenceError
from .models import EdgeIdentity
from .permissions import EdgeIdentityWithIdentifierViewPermissions

trait_schema = APITraitSchema()


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        pagination_class=EdgeIdentityPagination,
        paginator_inspectors=[EdgeIdentityPaginationInspector],
    ),
)
class EdgeIdentityViewSet(
    GenericViewSet,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    ListModelMixin,
):
    serializer_class = EdgeIdentitySerializer
    pagination_class = EdgeIdentityPagination
    lookup_field = "identity_uuid"
    dynamo_identifier_search_functions = {
        "EQUAL": lambda identifier: Key("identifier").eq(identifier),
        "BEGINS_WITH": lambda identifier: Key("identifier").begins_with(identifier),
    }

    def initial(self, request, *args, **kwargs):
        environment = self.get_environment_from_request()
        if not environment.project.enable_dynamo_db:
            raise DynamoNotEnabledError()

        super().initial(request, *args, **kwargs)

    def _get_search_function_and_value(
        self,
        search_query: str,
    ) -> typing.Tuple[typing.Callable, str]:
        if search_query.startswith('"') and search_query.endswith('"'):
            return self.dynamo_identifier_search_functions[
                "EQUAL"
            ], search_query.replace('"', "")
        return self.dynamo_identifier_search_functions["BEGINS_WITH"], search_query

    def get_object(self):
        return EdgeIdentity.dynamo_wrapper.get_item_from_uuid_or_404(
            self.kwargs["identity_uuid"]
        )

    def get_queryset(self):
        page_size = self.pagination_class().get_page_size(self.request)
        previous_last_evaluated_key = self.request.GET.get("last_evaluated_key")
        search_query = self.request.query_params.get("q")
        start_key = None
        if previous_last_evaluated_key:
            start_key = json.loads(base64.b64decode(previous_last_evaluated_key))

        if not search_query:
            return EdgeIdentity.dynamo_wrapper.get_all_items(
                self.kwargs["environment_api_key"], page_size, start_key
            )
        search_func, search_identifier = self._get_search_function_and_value(
            search_query
        )
        return EdgeIdentity.dynamo_wrapper.search_items_with_identifier(
            self.kwargs["environment_api_key"],
            search_identifier,
            search_func,
            page_size,
            start_key,
        )

    def get_permissions(self):
        return [
            IsAuthenticated(),
            NestedEnvironmentPermissions(
                action_permission_map={
                    "retrieve": VIEW_IDENTITIES,
                    "list": VIEW_IDENTITIES,
                    "create": MANAGE_IDENTITIES,
                    "get_traits": VIEW_IDENTITIES,
                    "update_traits": MANAGE_IDENTITIES,
                    "perform_destroy": MANAGE_IDENTITIES,
                },
            ),
        ]

    def get_environment_from_request(self):
        """
        Get environment object from URL parameters in request.
        """
        return Environment.objects.get(api_key=self.kwargs["environment_api_key"])

    def perform_destroy(self, instance):
        EdgeIdentity.dynamo_wrapper.delete_item(instance["composite_key"])

    @swagger_auto_schema(
        responses={200: EdgeIdentityTraitsSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="list-traits")
    def get_traits(self, request, *args, **kwargs):
        identity = self.get_object()
        data = trait_schema.dump(identity["identity_traits"], many=True)
        return Response(data=data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="put",
        request_body=EdgeIdentityTraitsSerializer,
        responses={200: EdgeIdentityTraitsSerializer()},
    )
    @action(detail=True, methods=["put"], url_path="update-traits")
    def update_traits(self, request, *args, **kwargs):
        environment = self.get_environment_from_request()
        if not environment.project.organisation.persist_trait_data:
            raise TraitPersistenceError()
        identity = build_identity_model(self.get_object())
        try:
            trait = trait_schema.load(request.data)
        except marshmallow.ValidationError as validation_error:
            raise ValidationError(validation_error) from validation_error
        _, traits_updated = identity.update_traits([trait])
        if traits_updated:
            EdgeIdentity.dynamo_wrapper.put_item(build_identity_dict(identity))

        data = trait_schema.dump(trait)
        return Response(data, status=status.HTTP_200_OK)


class EdgeIdentityFeatureStateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IdentityFeatureStatePermissions]
    lookup_field = "featurestate_uuid"

    serializer_class = EdgeIdentityFeatureStateSerializer

    # Patch is not supported
    http_method_names = [
        "get",
        "post",
        "put",
        "delete",
        "head",
        "options",
        "trace",
    ]
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        identity_document = EdgeIdentity.dynamo_wrapper.get_item_from_uuid_or_404(
            self.kwargs["edge_identity_identity_uuid"]
        )

        if (
            identity_document["environment_api_key"]
            != self.kwargs["environment_api_key"]
        ):
            raise PermissionDenied("Identity does not belong to this environment.")
        identity = EdgeIdentity.from_identity_document(identity_document)

        valid_feature_names = set(
            FeatureState.objects.filter(
                environment__api_key=identity.environment_api_key
            ).values_list("feature__name", flat=True)
        )
        identity.synchronise_features(valid_feature_names)
        self.identity = identity

    def get_object(self):
        if feature_state := self.identity.get_feature_state_by_featurestate_uuid(
            self.kwargs["featurestate_uuid"]
        ):
            return feature_state
        else:
            raise NotFound()

    @swagger_auto_schema(query_serializer=EdgeIdentityFsQueryparamSerializer())
    def list(self, request, *args, **kwargs):
        q_params_serializer = EdgeIdentityFsQueryparamSerializer(
            data=self.request.query_params
        )
        q_params_serializer.is_valid(raise_exception=True)

        identity_features = self.identity.feature_overrides

        if feature := q_params_serializer.data.get("feature"):
            identity_features = filter(
                lambda fs: fs.feature.id == feature, identity_features
            )

        serializer = self.get_serializer(identity_features, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        self.identity.remove_feature_override(instance)
        self.identity.save(
            user=self.request.user.id,
            master_api_key=getattr(self.request, "master_api_key", None),
        )

    @swagger_auto_schema(responses={200: IdentityAllFeatureStatesSerializer(many=True)})
    @action(detail=False, methods=["GET"])
    def all(self, request, *args, **kwargs):
        (
            feature_states,
            identity_feature_names,
        ) = self.identity.get_all_feature_states()

        serializer = IdentityAllFeatureStatesSerializer(
            instance=feature_states,
            many=True,
            context={
                "request": request,
                "identity": self.identity,
                "environment_api_key": self.identity.environment_api_key,
                "identity_feature_names": identity_feature_names,
            },
        )

        return Response(serializer.data)


class EdgeIdentityWithIdentifierFeatureStateView(APIView):
    permission_classes = [IsAuthenticated, EdgeIdentityWithIdentifierViewPermissions]
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        serializer = EdgeIdentityIdentifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if identity_document := EdgeIdentity.dynamo_wrapper.get_item(
            f"{self.kwargs['environment_api_key']}_{serializer.data['identifier']}"
        ):
            self.identity = EdgeIdentity.from_identity_document(identity_document)
        else:
            raise NotFound()

    @swagger_auto_schema(
        request_body=EdgeIdentityWithIdentifierFeatureStateRequestBody,
        responses={200: EdgeIdentityFeatureStateSerializer()},
    )
    def put(self, request, *args, **kwargs):
        feature = request.data.get("feature")
        feature_state = self.identity.get_feature_state_by_feature_name_or_id(feature)
        serializer = EdgeIdentityFeatureStateSerializer(
            instance=feature_state,
            data=request.data,
            context={"view": self, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        request_body=EdgeIdentityWithIdentifierFeatureStateDeleteRequestBody,
    )
    def delete(self, request, *args, **kwargs):
        feature = request.data.get("feature")
        if feature_state := self.identity.get_feature_state_by_feature_name_or_id(
            feature
        ):
            self.identity.remove_feature_override(feature_state)
            self.identity.save(
                user=request.user.id,
                master_api_key=getattr(request, "master_api_key", None),
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
