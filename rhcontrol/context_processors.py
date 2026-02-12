from django.conf import settings

def company_info(request):
    """
    Disponibiliza os dados da empresa em todos os templates.
    """
    return {
        'company_name_settings': settings.COMPANY_NAME,
        'company_cnpj': settings.COMPANY_CNPJ,
        'company_address': settings.COMPANY_ADDRESS,
        'company_neighborhood': settings.COMPANY_NEIGHBORHOOD,
        'company_state': settings.COMPANY_STATE,
        'company_zip': settings.COMPANY_ZIP,
        'company_phone': settings.COMPANY_PHONE,
        'company_email': settings.COMPANY_EMAIL,
        'company_agency': settings.COMPANY_AGENCY,
    }