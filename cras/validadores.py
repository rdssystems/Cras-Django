from django.core.exceptions import ValidationError


def validar_cpf(cpf):
    """Aceita vazio ou 11 números com dígitos verificadores corretos; devolve o CPF."""
    if not cpf:
        return ''
    if not cpf.isascii() or not cpf.isdigit():
        raise ValidationError('Digite somente números, sem pontos ou traços.')
    if len(cpf) != 11:
        raise ValidationError('O CPF deve ter exatamente 11 números.')
    if len(set(cpf)) == 1:
        raise ValidationError('Informe um CPF válido.')

    numeros = [int(digito) for digito in cpf]
    primeiro = 11 - sum(numeros[indice] * (10 - indice) for indice in range(9)) % 11
    primeiro = 0 if primeiro >= 10 else primeiro
    segundo = 11 - sum(numeros[indice] * (11 - indice) for indice in range(10)) % 11
    segundo = 0 if segundo >= 10 else segundo
    if numeros[9:] != [primeiro, segundo]:
        raise ValidationError('Informe um CPF válido.')
    return cpf


def validar_cep(cep):
    """Aceita vazio ou 8 números (com ou sem ponto e hífen) e devolve 00000-000."""
    if not cep:
        return ''
    numeros = cep.replace('.', '').replace('-', '').replace(' ', '')
    if not (numeros.isdigit() and len(numeros) == 8):
        raise ValidationError('O CEP tem 8 números.')
    return f'{numeros[:5]}-{numeros[5:]}'
