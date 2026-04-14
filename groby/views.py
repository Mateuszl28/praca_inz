import json
from collections import Counter
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.urls import reverse
from .models import Osoba, Grob, Sektor


SZYDLOW_CENTRUM = (50.5847, 20.8327)


def home(request):
    context = {
        'liczba_osob': Osoba.objects.count(),
        'liczba_grobow': Grob.objects.count(),
        'liczba_sektorow': Sektor.objects.count(),
    }
    return render(request, 'groby/home.html', context)


def szukaj(request):
    query = request.GET.get('q', '').strip()
    sektor_id = request.GET.get('sektor', '').strip()
    typ = request.GET.get('typ', '').strip()
    rok_od = request.GET.get('rok_od', '').strip()
    rok_do = request.GET.get('rok_do', '').strip()

    osoby = Osoba.objects.select_related('grob', 'grob__sektor')

    if query:
        osoby = osoby.filter(
            Q(nazwisko__icontains=query)
            | Q(imie__icontains=query)
            | Q(nazwisko_rodowe__icontains=query)
        )
    if sektor_id:
        osoby = osoby.filter(grob__sektor_id=sektor_id)
    if typ:
        osoby = osoby.filter(grob__typ=typ)
    if rok_od.isdigit():
        osoby = osoby.filter(data_smierci__year__gte=int(rok_od))
    if rok_do.isdigit():
        osoby = osoby.filter(data_smierci__year__lte=int(rok_do))

    osoby = osoby.order_by('nazwisko', 'imie')
    total = osoby.count()

    paginator = Paginator(osoby, 20)
    page = paginator.get_page(request.GET.get('page'))

    aktywne_filtry = bool(query or sektor_id or typ or rok_od or rok_do)

    params = request.GET.copy()
    params.pop('page', None)
    querystring_bez_page = params.urlencode()

    context = {
        'query': query,
        'sektor_id': sektor_id,
        'typ': typ,
        'rok_od': rok_od,
        'rok_do': rok_do,
        'page': page,
        'total': total,
        'sektory': Sektor.objects.order_by('nazwa'),
        'typy': Grob.TYP_CHOICES,
        'aktywne_filtry': aktywne_filtry,
        'querystring_bez_page': querystring_bez_page,
    }
    return render(request, 'groby/szukaj.html', context)


def sektory_list(request):
    sektory = Sektor.objects.annotate(
        liczba_grobow=Count('groby', distinct=True),
        liczba_osob=Count('groby__osoby', distinct=True),
    ).order_by('nazwa')
    return render(request, 'groby/sektory_list.html', {'sektory': sektory})


def sektor_detail(request, pk):
    sektor = get_object_or_404(Sektor, pk=pk)
    groby = sektor.groby.prefetch_related('osoby').order_by('numer')
    paginator = Paginator(groby, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'groby/sektor_detail.html', {'sektor': sektor, 'page': page})


def grob_detail(request, pk):
    grob = get_object_or_404(Grob.objects.select_related('sektor').prefetch_related('osoby'), pk=pk)
    return render(request, 'groby/grob_detail.html', {'grob': grob})


def statystyki(request):
    typy_labels = dict(Grob.TYP_CHOICES)
    typy_qs = Grob.objects.values('typ').annotate(c=Count('id')).order_by('-c')
    typy = [{'label': typy_labels.get(t['typ'], t['typ']), 'value': t['c']} for t in typy_qs]

    sektor_qs = Sektor.objects.annotate(liczba=Count('groby')).values('nazwa', 'liczba').order_by('nazwa')
    sektory_dane = [{'label': f"Sektor {s['nazwa']}", 'value': s['liczba']} for s in sektor_qs]

    dekady_counter = Counter()
    for ds in Osoba.objects.filter(data_smierci__isnull=False).values_list('data_smierci', flat=True):
        dekady_counter[(ds.year // 10) * 10] += 1
    dekady = [{'label': f'{d}.', 'value': v} for d, v in sorted(dekady_counter.items())]

    wieki = []
    for o in Osoba.objects.filter(data_urodzenia__isnull=False, data_smierci__isnull=False):
        w = o.wiek
        if w is not None and w >= 0:
            wieki.append(w)

    sredni_wiek = round(sum(wieki) / len(wieki), 1) if wieki else 0
    najstarsza = max(wieki) if wieki else 0
    najmlodsza = min(wieki) if wieki else 0

    osob_na_grob_counter = Counter()
    for g in Grob.objects.annotate(lo=Count('osoby')).values_list('lo', flat=True):
        osob_na_grob_counter[g] += 1
    osob_na_grob = [{'label': f'{k} osoba' if k == 1 else f'{k} osób', 'value': v} for k, v in sorted(osob_na_grob_counter.items())]

    context = {
        'typy_json': json.dumps(typy, ensure_ascii=False),
        'sektory_json': json.dumps(sektory_dane, ensure_ascii=False),
        'dekady_json': json.dumps(dekady, ensure_ascii=False),
        'osob_na_grob_json': json.dumps(osob_na_grob, ensure_ascii=False),
        'sredni_wiek': sredni_wiek,
        'najstarsza': najstarsza,
        'najmlodsza': najmlodsza,
        'liczba_osob': Osoba.objects.count(),
        'liczba_grobow': Grob.objects.count(),
        'liczba_sektorow': Sektor.objects.count(),
    }
    return render(request, 'groby/statystyki.html', context)


def mapa(request):
    groby = Grob.objects.filter(
        szerokosc_geo__isnull=False,
        dlugosc_geo__isnull=False,
    ).select_related('sektor').prefetch_related('osoby')

    dane = []
    for g in groby:
        osoby_str = [
            f'{o.imie} {o.nazwisko}' + (f' (z d. {o.nazwisko_rodowe})' if o.nazwisko_rodowe else '')
            for o in g.osoby.all()
        ]
        dane.append({
            'lat': g.szerokosc_geo,
            'lng': g.dlugosc_geo,
            'sektor': g.sektor.nazwa,
            'numer': g.numer,
            'typ': g.get_typ_display(),
            'osoby': osoby_str,
            'url': reverse('groby:grob_detail', args=[g.pk]),
        })

    context = {
        'groby_json': json.dumps(dane, ensure_ascii=False),
        'liczba': len(dane),
        'centrum_lat': SZYDLOW_CENTRUM[0],
        'centrum_lng': SZYDLOW_CENTRUM[1],
    }
    return render(request, 'groby/mapa.html', context)


def osoba_detail(request, pk):
    osoba = get_object_or_404(Osoba.objects.select_related('grob', 'grob__sektor'), pk=pk)
    return render(request, 'groby/osoba_detail.html', {'osoba': osoba})
