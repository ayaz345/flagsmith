import typing

from django.db.models import Model, Q
from django.http import HttpRequest
from rest_framework import exceptions
from rest_framework.permissions import BasePermission, IsAuthenticated

from environments.models import Environment
from environments.permissions.constants import VIEW_ENVIRONMENT
from projects.models import Project


class EnvironmentKeyPermissions(BasePermission):
    def has_permission(self, request, view):
        # Authentication class will set the environment on the request if it exists
        if hasattr(request, "environment"):
            return True

        raise exceptions.PermissionDenied("Missing or invalid Environment Key")

    def has_object_permission(self, request, view, obj):
        """
        This method is only called if has_permission returns true so we can safely return true for all requests here.
        """
        return True


class EnvironmentPermissions(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if view.action == "create":
            try:
                project_id = request.data.get("project")
                project_lookup = Q(id=project_id)
                project = Project.objects.get(project_lookup)
                return request.user.has_project_permission(
                    "CREATE_ENVIRONMENT", project
                )
            except Project.DoesNotExist:
                return False

        # return true as all users can list and obj permissions will be handled later
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_anonymous:
            return False

        if view.action == "clone":
            return request.user.is_project_admin(obj.project)

        return request.user.is_environment_admin(obj) or view.action in [
            "user_permissions"
        ]


class MasterAPIKeyEnvironmentPermissions(BasePermission):
    def has_permission(self, request: HttpRequest, view: str) -> bool:
        master_api_key = getattr(request, "master_api_key", None)

        if not master_api_key:
            return False

        if view.action == "create":
            try:
                project_id = request.data.get("project")
                project = Project.objects.get(id=project_id)
                return master_api_key.organisation_id == project.organisation.id

            except Project.DoesNotExist:
                return False

        # return true as list will be handled by view and obj permissions will be handled later
        return True

    def has_object_permission(
        self, request: HttpRequest, view: str, obj: Model
    ) -> bool:
        if master_api_key := getattr(request, "master_api_key", None):
            return master_api_key.organisation_id == obj.project.organisation_id
        else:
            return False


class IdentityPermissions(BasePermission):
    def has_permission(self, request, view):
        try:
            if view.action == "create":
                environment_api_key = view.kwargs.get("environment_api_key")
                environment = Environment.objects.get(api_key=environment_api_key)
                if not request.user.is_environment_admin(environment):
                    return False

            # return true as all users can list and specific object permissions will be handled later
            return view.detail

        except Environment.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_organisation_admin(obj.environment.project.organisation):
            return True

        return bool(request.user.is_environment_admin(obj.environment))


class NestedEnvironmentPermissions(BasePermission):
    def __init__(
        self,
        *args,
        action_permission_map: typing.Dict[str, str] = None,
        get_environment_from_object_callable: typing.Callable[
            [Model], Environment
        ] = lambda o: o.environment,
        admin_actions: typing.Iterable[str] = None,
        **kwargs,
    ):
        super(NestedEnvironmentPermissions, self).__init__(*args, **kwargs)

        self.action_permission_map = action_permission_map or {}
        self.action_permission_map.setdefault("list", VIEW_ENVIRONMENT)

        self.get_environment_from_object_callable = get_environment_from_object_callable

    def has_permission(self, request, view):
        try:
            environment_api_key = view.kwargs.get("environment_api_key")
            environment = Environment.objects.get(api_key=environment_api_key)
        except Environment.DoesNotExist:
            return False

        if view.action in self.action_permission_map:
            return request.user.has_environment_permission(
                self.action_permission_map[view.action], environment
            )
        elif view.action == "create":
            # default to always allow environment admins to create
            return request.user.is_environment_admin(environment)

        return view.detail

    def has_object_permission(self, request, view, obj):
        if view.action in self.action_permission_map:
            return request.user.has_environment_permission(
                self.action_permission_map[view.action],
                self.get_environment_from_object_callable(obj),
            )

        return request.user.is_environment_admin(
            self.get_environment_from_object_callable(obj)
        )


class TraitPersistencePermissions(BasePermission):
    message = "Organisation is not authorised to store traits."

    def has_permission(self, request, view):
        # this permission class will only work when placed after
        # EnvironmentKeyPermissions class in a view
        return request.environment.project.organisation.persist_trait_data

    def has_object_permission(self, request, view, obj):
        # no views that use this permission currently have any detail endpoints
        return False


class EnvironmentAdminPermission(BasePermission):
    def has_permission(self, request, view):
        try:
            environment = Environment.objects.get(
                api_key=view.kwargs.get("environment_api_key")
            )
            return request.user.is_environment_admin(environment)
        except Environment.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        return request.user.is_environment_admin(obj.environment)
