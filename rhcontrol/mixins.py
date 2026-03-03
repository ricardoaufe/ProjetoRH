"""
Reusable mixins for rhcontrol views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RhAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that enforces two conditions:

    1. The user must be authenticated (handled by LoginRequiredMixin —
       unauthenticated users are redirected to the login page).
    2. The authenticated user must belong to the Django auth Group named
       'RhAdmin'. If not, an HTTP 403 Forbidden response is raised.

    Usage
    -----
    class MyView(RhAdminRequiredMixin, TemplateView):
        template_name = "..."
    """

    # When test_func returns False, raise PermissionDenied (→ 403) instead of
    # redirecting to the login page again.
    raise_exception = True

    def test_func(self):
        return self.request.user.groups.filter(name='RhAdmin').exists()
