from django.contrib.auth.models import Permission
from django.db.models import Q

RH_PERMISSION_MATRIX = {
    'Funcionários': {
        'model': 'employee',
        'actions': {
            'read': 'view_employee',
            'create': 'add_employee',
            'update': 'change_employee',
            'delete': 'delete_employee',
        }
},
    'Férias': {
        'model': 'vacation',
        'actions': {
            'read': 'view_vacation',
            'create': 'add_vacation',
            'update': 'change_vacation',
            'delete': 'delete_vacation',
        }
},
    'Treinamentos': {
        'model': 'training',
        'actions': {
            'read': 'view_training',
            'create': 'add_training',
            'update': 'change_training',
            'delete': 'delete_training',
        }
},
    'Setores': {
        'model': 'department',
        'actions': {
            'read': 'view_department',
            'create': 'add_department',
            'update': 'change_department',
            'delete': 'delete_department',
        }
},
    'Cargos': {
        'model': 'jobtitle',
        'actions': {
            'read': 'view_jobtitle',
            'create': 'add_jobtitle',
            'update': 'change_jobtitle',
            'delete': 'delete_jobtitle',
        }
},
    'Plano de Carreira': {
        'model': 'careerplan',
        'actions': {
            'read': 'view_careerplan',
            'create': 'add_careerplan',
            'update': 'change_careerplan',
            'delete': 'delete_careerplan',
        }
}, 
    'Ocorrência': {
        'model': 'occurrence',
        'actions': {
            'read': 'view_occurrence',
            'create': 'add_occurrence',
            'update': 'change_occurrence',
            'delete': 'delete_occurrence',
        }
},
    'Usuários': {
        'app_label': 'auth',
        'model': 'user',
        'actions': {
            'read': 'view_user',
            'create': 'add_user',
            'update': 'change_user',
            'delete': 'delete_user',
        }
},
    'Perfis de Acesso': {
        'app_label': 'auth',
        'model': 'group',
        'actions': {
            'read': 'view_group',
            'create': 'add_group',
            'update': 'change_group',
            'delete': 'delete_group',
        }
}
}


def get_matrix_permissions(codenames):
    """
    Converte os codenames enviados pelo formulário em Permissions,
    aceitando apenas as que existem na RH_PERMISSION_MATRIX.

    O POST vem do navegador e pode ser editado: sem esse filtro, qualquer
    codename do sistema (admin, sessions, ...) poderia ser atribuído a um perfil.
    """
    selected = set(codenames)
    query = Q(pk__in=[])
    for entry in RH_PERMISSION_MATRIX.values():
        allowed = selected & set(entry['actions'].values())
        if allowed:
            query |= Q(
                content_type__app_label=entry.get('app_label', 'rhcontrol'),
                content_type__model=entry['model'],
                codename__in=allowed,
            )
    return Permission.objects.filter(query)
