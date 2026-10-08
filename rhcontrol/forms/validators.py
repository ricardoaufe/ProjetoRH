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