"""
Sieć alejek cmentarza jako graf — podstawa wskazówek dojścia do grobu.

Alejki są rysowane przez staff na planie jako łamane (listy punktów w pikselach
skanu). Tu zamieniamy je na graf nieskierowany:
  * punkty leżące bliżej niż `tolerancja` scalamy w jeden węzeł (skrzyżowania),
  * odcinek, na którym leży węzeł innej alejki, dzielimy w tym węźle
    (alejka dochodząca „w bok” innej tworzy rozwidlenie).

Samo wyznaczanie trasy (Dijkstra) odbywa się w przeglądarce, żeby działało
także offline — patrz templates/groby/mapa.html.
"""
from math import hypot

TOLERANCJA_PX = 30.0


def _rzut_na_odcinek(p, a, b):
    """Zwraca (t, odległość) rzutu punktu p na odcinek a–b; t w [0, 1]."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    dl2 = dx * dx + dy * dy
    if dl2 == 0:
        return 0.0, hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / dl2
    t = max(0.0, min(1.0, t))
    return t, hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def zbuduj_graf(alejki, tolerancja=TOLERANCJA_PX):
    """
    alejki: iterowalne par (nazwa, punkty), punkty = [[x, y], ...].
    Zwraca {'wezly': [[x, y], ...], 'krawedzie': [[i, j, nazwa], ...]}.
    """
    wezly = []

    def indeks_wezla(p):
        for i, w in enumerate(wezly):
            if hypot(w[0] - p[0], w[1] - p[1]) <= tolerancja:
                return i
        wezly.append([float(p[0]), float(p[1])])
        return len(wezly) - 1

    odcinki = []
    for nazwa, punkty in alejki:
        poprzedni = None
        for p in punkty or []:
            try:
                x, y = float(p[0]), float(p[1])
            except (TypeError, ValueError, IndexError):
                continue
            i = indeks_wezla((x, y))
            if poprzedni is not None and poprzedni != i:
                odcinki.append((poprzedni, i, nazwa or ''))
            poprzedni = i

    # Podział odcinków w węzłach leżących na nich (rozwidlenia typu „T”).
    zmieniono = True
    while zmieniono:
        zmieniono = False
        for k, (a, b, nazwa) in enumerate(odcinki):
            for i, w in enumerate(wezly):
                if i in (a, b):
                    continue
                t, odl = _rzut_na_odcinek(w, wezly[a], wezly[b])
                if odl <= tolerancja and 0.0 < t < 1.0:
                    odcinki[k:k + 1] = [(a, i, nazwa), (i, b, nazwa)]
                    zmieniono = True
                    break
            if zmieniono:
                break

    krawedzie, widziane = [], set()
    for a, b, nazwa in odcinki:
        klucz = (min(a, b), max(a, b))
        if klucz in widziane:
            continue
        widziane.add(klucz)
        krawedzie.append([a, b, nazwa])
    return {'wezly': wezly, 'krawedzie': krawedzie}
