"""Globalny kontekst dostępny we wszystkich szablonach."""
from datetime import date


def _wielkanoc(rok):
    """Algorytm Gaussa — niedziela wielkanocna."""
    a = rok % 19
    b = rok // 100
    c = rok % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    miesiac = (h + L - 7 * m + 114) // 31
    dzien = ((h + L - 7 * m + 114) % 31) + 1
    return date(rok, miesiac, dzien)


def banner_kontekst(request):
    dzis = date.today()
    # Wszystkich Świętych: 25.10 - 04.11
    banner_ws = (dzis.month == 10 and dzis.day >= 25) or (dzis.month == 11 and dzis.day <= 4)
    # Boże Narodzenie: 20.12 - 06.01
    banner_bn = (dzis.month == 12 and dzis.day >= 20) or (dzis.month == 1 and dzis.day <= 6)
    # Wielkanoc: tydzień przed do tygodnia po
    try:
        ws = _wielkanoc(dzis.year)
        delta = (dzis - ws).days
        banner_we = -7 <= delta <= 7
    except Exception:
        banner_we = False
    return {
        'banner_wszystkich_swietych': banner_ws,
        'banner_boze_narodzenie': banner_bn,
        'banner_wielkanoc': banner_we,
        'data_dzis': dzis,
    }
