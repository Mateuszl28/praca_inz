"""Globalny kontekst dostępny we wszystkich szablonach."""
from datetime import date


def banner_kontekst(request):
    dzis = date.today()
    # Banner Wszystkich Świętych: 25.10 - 04.11
    banner_ws = (dzis.month == 10 and dzis.day >= 25) or (dzis.month == 11 and dzis.day <= 4)
    return {
        'banner_wszystkich_swietych': banner_ws,
        'data_dzis': dzis,
    }
