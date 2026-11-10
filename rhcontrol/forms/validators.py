import os

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_cpf(cpf):
    if not cpf:
        return False

    clean_cpf = "".join([c for c in cpf if c.isdigit()])

    if len(clean_cpf) != 11:
        return False

    if clean_cpf == clean_cpf[0] * 11:
        return False

    add = sum(int(clean_cpf[i]) * (10 - i) for i in range(9))
    rest = (add * 10) % 11
    if rest == 10:
        rest = 0
    if rest != int(clean_cpf[9]):
        return False

    add = sum(int(clean_cpf[i]) * (11 - i) for i in range(10))
    rest = (add * 10) % 11
    if rest == 10:
        rest = 0
    return rest == int(clean_cpf[10])


# Assinatura (primeiros bytes) de cada tipo aceito: um .exe renomeado para
# .pdf tem a extensão certa, mas não começa com %PDF e é recusado.
DOCUMENT_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


def validate_training_document(uploaded):
    """Aceita só PDF, JPG ou PNG verdadeiros, até TRAINING_DOCUMENT_MAX_SIZE."""
    name = uploaded.name
    ext = os.path.splitext(name)[1].lower()
    if ext not in DOCUMENT_SIGNATURES:
        raise ValidationError(
            f'"{name}": tipo de arquivo não permitido. Envie PDF, JPG ou PNG.'
        )

    max_size = settings.TRAINING_DOCUMENT_MAX_SIZE
    if uploaded.size > max_size:
        raise ValidationError(
            f'"{name}" passa do limite de {max_size // (1024 * 1024) or 1} MB.'
        )

    uploaded.seek(0)
    header = uploaded.read(8)
    uploaded.seek(0)
    if not header.startswith(DOCUMENT_SIGNATURES[ext]):
        raise ValidationError(
            f'"{name}" não é um {ext[1:].upper()} válido (o conteúdo não confere com a extensão).'
        )
