from .auth import (
    change_password,
    login_create,
    login_view,
    logout_view,
    profile_view,
)
from .career import (
    cancel_career_plan,
    career_plan_create,
    career_plan_delete,
    career_plan_list,
    career_plan_update,
    confirm_career_plan_action,
)
from .dashboard import dashboard_view, upcoming_events_view
from .department import (
    ajax_load_jobs_by_department,
    department_create,
    department_delete,
    department_list,
    department_update,
)
from .employee import (
    ajax_load_employee_data,
    delete_history_log,
    employee_create,
    employee_delete,
    employee_update,
    employee_view,
    history_create_view,
    history_edit_view,
)
from .excel import (
    create_employee_list_xlsx,
    training_attendance_sheet,
    training_on_the_job_sheet,
)
from .pdf import (
    create_bank_presentation_pdf,
    create_benefits_acquisition_pdf,
    create_commitment_term_pdf,
    create_confidenciality_pdf,
    create_department_and_jobtitle_pdf,
    create_employee_list_pdf,
    create_employee_registration_pdf,
    create_employees_department_pdf,
    create_image_consent_pdf,
    create_internal_regulation_pdf,
    create_occurrence_list_pdf,
    create_personal_data_consent_pdf,
    create_responsible_term_pdf,
    create_training_attendance_pdf,
    create_training_list_pdf,
    create_vacation_list_pdf,
    employee_career_plan_pdf,
)
from .role import role_create_view, role_delete_view, role_list_view, role_update_view
from .training import (
    training_create,
    training_delete,
    training_document_view,
    training_update,
    training_view,
)
from .user import user_create_view, user_delete_view, user_list_view, user_update_view
from .vacation import vacation_create, vacation_delete, vacation_update, vacation_view
