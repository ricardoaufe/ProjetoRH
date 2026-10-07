# forms/__init__.py
from .access import RoleGroupForm, SystemUserForm, SystemUserUpdateForm
from .auth import LoginForm, UserUpdateForm
from .career import CareerPlanForm
from .employee import (
    DependentForm,
    DependentFormSet,
    EmployeeForm,
    EmployeeHistoryForm,
)
from .occurrence import OccurrenceForm
from .organization import DepartmentForm, JobTitleForm, JobTitleFormSet
from .training import TrainingForm
from .vacation import VacationForm
from .validators import validate_cpf

__all__ = [
    "CareerPlanForm",
    "DepartmentForm",
    "DependentForm",
    "DependentFormSet",
    "EmployeeForm",
    "EmployeeHistoryForm",
    "JobTitleForm",
    "JobTitleFormSet",
    "LoginForm",
    "OccurrenceForm",
    "RoleGroupForm",
    "SystemUserForm",
    "SystemUserUpdateForm",
    "TrainingForm",
    "UserUpdateForm",
    "VacationForm",
    "validate_cpf",
]