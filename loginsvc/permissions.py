from django.utils.translation import ugettext as _
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    message = _('Only authorized users are allowed to access this API')

    def has_permission(self, request, view):
        user = request.user

        return user and user.is_staff


def is_staff(user):
    return user and user.groups.filter(name='staff_grp').exists()


class IsStaff(permissions.BasePermission):
    message = _('Only authorized user are allowed to access this API')

    def has_permission(self, request, view):
        user = request.user

        return is_staff(user)
