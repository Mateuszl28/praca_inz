import io
import json
from collections import Counter, defaultdict
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_POST
from .models import (
    Osoba, Grob, Sektor, Zdjecie, Relacja, Zgloszenie, Profil, HistoriaZmian,
    Wspomnienie, Swieca, ZapisaneSzukanie, Wpis,
    Tag, Panorama, HotspotPanoramy, SubskrypcjaPush, TokenLogowania,
)


SZYDLOW_CENTRUM = (50.5847, 20.8327)


def _antybot(request):
    """Honeypot + minimalny czas wypełnienia. Zwraca True jeśli to bot."""
    import time
    if (request.POST.get('_pulapka') or '').strip():
        return True
    try:
        ts = float(request.POST.get('_ts', '0'))
        if time.time() - ts < 2.0:
            return True
    except (ValueError, TypeError):
        return True
    return False


def _pole_antybot_html():
    import time
    return (
        f'<input type="text" name="_pulapka" tabindex="-1" autocomplete="off" '
        f'style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;" aria-hidden="true">'
        f'<input type="hidden" name="_ts" value="{time.time():.0f}">'
    )


def _szukaj_fts(osoby_qs, query):
    """SQLite FTS5 z fallbackiem na icontains. Wspiera prefiksy (Kowal* -> Kowalski)."""
    from django.db import connection
    try:
        with connection.cursor() as cur:
            tokeny = [t for t in query.replace('"', '').split() if t]
            if not tokeny:
                return osoby_qs.none()
            fts_q = ' '.join(t + '*' for t in tokeny)
            cur.execute('SELECT rowid FROM osoba_fts WHERE osoba_fts MATCH %s LIMIT 5000', [fts_q])
            ids = [r[0] for r in cur.fetchall()]
        if ids:
            return osoby_qs.filter(pk__in=ids)
        return osoby_qs.none()
    except Exception:
        return osoby_qs.filter(
            Q(nazwisko__icontains=query)
            | Q(imie__icontains=query)
            | Q(nazwisko_rodowe__icontains=query)
        )


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
        osoby = _szukaj_fts(osoby, query)
    if sektor_id:
        osoby = osoby.filter(grob__sektor_id=sektor_id)
    if typ:
        osoby = osoby.filter(grob__typ=typ)
    if rok_od.isdigit():
        osoby = osoby.filter(data_smierci__year__gte=int(rok_od))
    if rok_do.isdigit():
        osoby = osoby.filter(data_smierci__year__lte=int(rok_do))

    tag_slug = request.GET.get('tag', '').strip()
    if tag_slug:
        osoby = osoby.filter(tagi__slug=tag_slug)

    osoby = osoby.order_by('nazwisko', 'imie').distinct()
    total = osoby.count()

    sugestia = None
    if query and total == 0:
        sugestia = _zaproponuj_nazwisko(query)

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
        'sugestia': sugestia,
        'tagi': Tag.objects.all(),
        'aktywny_tag': tag_slug,
    }
    return render(request, 'groby/szukaj.html', context)


def _zaproponuj_nazwisko(query):
    """Najbliższe nazwisko/imie do zapytania, używając difflib."""
    import difflib
    fraza = query.strip().lower()
    if len(fraza) < 3:
        return None
    nazwiska = set()
    for n, i in Osoba.objects.values_list('nazwisko', 'imie'):
        if n: nazwiska.add(n)
        if i: nazwiska.add(i)
    bliskie = difflib.get_close_matches(fraza, [n.lower() for n in nazwiska], n=1, cutoff=0.7)
    if not bliskie:
        return None
    bliska_lower = bliskie[0]
    for n in nazwiska:
        if n.lower() == bliska_lower:
            return n
    return None


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
    grob = get_object_or_404(
        Grob.objects.select_related('sektor').prefetch_related('osoby', 'zdjecia'),
        pk=pk,
    )
    obserwuje = False
    if request.user.is_authenticated:
        obserwuje = grob.obserwujacy.filter(user=request.user).exists()
    return render(request, 'groby/grob_detail.html', {
        'grob': grob,
        'zdjecia': grob.zdjecia.all(),
        'obserwuje': obserwuje,
    })


def o_cmentarzu(request):
    return render(request, 'groby/o_cmentarzu.html')


def sugestie(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    osoby = (
        Osoba.objects
        .filter(Q(nazwisko__istartswith=q) | Q(imie__istartswith=q) | Q(nazwisko_rodowe__istartswith=q))
        .select_related('grob', 'grob__sektor')
        .order_by('nazwisko', 'imie')[:8]
    )
    data = []
    for o in osoby:
        rodowe = f' (z d. {o.nazwisko_rodowe})' if o.nazwisko_rodowe else ''
        rok_ur = o.data_urodzenia.year if o.data_urodzenia else '?'
        rok_sm = o.data_smierci.year if o.data_smierci else '?'
        data.append({
            'nazwa': f'{o.imie} {o.nazwisko}{rodowe}',
            'lata': f'{rok_ur} — {rok_sm}',
            'grob': f'Sektor {o.grob.sektor.nazwa} · nr {o.grob.numer}',
            'url': reverse('groby:osoba_detail', args=[o.pk]),
        })
    return JsonResponse({'results': data})


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

    heatmapa = defaultdict(lambda: [0]*12)
    for ds in Osoba.objects.filter(data_smierci__isnull=False).values_list('data_smierci', flat=True):
        dekada = (ds.year // 10) * 10
        heatmapa[dekada][ds.month - 1] += 1
    heatmapa_dane = [{'dekada': f'{d}.', 'wartosci': heatmapa[d]} for d in sorted(heatmapa)]
    miesiace = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru']

    context = {
        'typy_json': json.dumps(typy, ensure_ascii=False),
        'sektory_json': json.dumps(sektory_dane, ensure_ascii=False),
        'dekady_json': json.dumps(dekady, ensure_ascii=False),
        'osob_na_grob_json': json.dumps(osob_na_grob, ensure_ascii=False),
        'heatmapa_json': json.dumps(heatmapa_dane, ensure_ascii=False),
        'miesiace_json': json.dumps(miesiace, ensure_ascii=False),
        'sredni_wiek': sredni_wiek,
        'najstarsza': najstarsza,
        'najmlodsza': najmlodsza,
        'liczba_osob': Osoba.objects.count(),
        'liczba_grobow': Grob.objects.count(),
        'liczba_sektorow': Sektor.objects.count(),
    }
    return render(request, 'groby/statystyki.html', context)


def mapa(request):
    from django.conf import settings
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None

    sektor_id = request.GET.get('sektor', '').strip()
    typ = request.GET.get('typ', '').strip()
    rok_od = request.GET.get('rok_od', '').strip()
    rok_do = request.GET.get('rok_do', '').strip()

    groby = Grob.objects.filter(
        plan_x__isnull=False,
        plan_y__isnull=False,
    ).select_related('sektor').prefetch_related('osoby').distinct()

    if sektor_id:
        groby = groby.filter(sektor_id=sektor_id)
    if typ:
        groby = groby.filter(typ=typ)
    if rok_od.isdigit():
        groby = groby.filter(osoby__data_smierci__year__gte=int(rok_od))
    if rok_do.isdigit():
        groby = groby.filter(osoby__data_smierci__year__lte=int(rok_do))

    dane = []
    for g in groby:
        osoby_str = [
            f'{o.imie} {o.nazwisko}' + (f' (z d. {o.nazwisko_rodowe})' if o.nazwisko_rodowe else '')
            for o in g.osoby.all()
        ]
        dane.append({
            'id': g.pk,
            'x': g.plan_x,
            'y': g.plan_y,
            'sektor': g.sektor.nazwa,
            'rzad': g.rzad,
            'numer': g.numer,
            'typ': g.get_typ_display(),
            'osoby': osoby_str,
            'url': reverse('groby:grob_detail', args=[g.pk]),
        })

    plan_url = settings.MEDIA_URL + settings.PLAN_IMAGE if settings.PLAN_IMAGE else None
    plan_w = plan_h = 0
    if plan_url:
        try:
            sciezka = settings.MEDIA_ROOT / settings.PLAN_IMAGE
            with Image.open(sciezka) as im:
                plan_w, plan_h = im.size
        except (FileNotFoundError, OSError):
            plan_url = None

    tryb_edycji = request.user.is_authenticated and request.user.is_staff

    context = {
        'groby_json': json.dumps(dane, ensure_ascii=False),
        'liczba': len(dane),
        'liczba_wszystkich': Grob.objects.count(),
        'plan_url': plan_url,
        'plan_w': plan_w,
        'plan_h': plan_h,
        'tryb_edycji': tryb_edycji,
        'sektory': Sektor.objects.order_by('nazwa'),
        'typy': Grob.TYP_CHOICES,
        'sektor_id': sektor_id,
        'typ': typ,
        'rok_od': rok_od,
        'rok_do': rok_do,
        'aktywne_filtry': bool(sektor_id or typ or rok_od or rok_do),
    }
    return render(request, 'groby/mapa.html', context)


def zapisz_pozycje(request):
    from django.http import JsonResponse, HttpResponseNotAllowed
    from django.contrib.auth.decorators import login_required

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'ok': False, 'error': 'Brak uprawnień'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
        grob_id = int(payload.get('grob_id'))
        x = float(payload.get('x'))
        y = float(payload.get('y'))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Nieprawidłowe dane'}, status=400)

    try:
        grob = Grob.objects.select_related('sektor').get(pk=grob_id)
    except Grob.DoesNotExist:
        return JsonResponse({'ok': False, 'error': f'Grób {grob_id} nie istnieje'}, status=404)

    grob.plan_x = x
    grob.plan_y = y
    grob.save(update_fields=['plan_x', 'plan_y', 'data_modyfikacji'])
    tytul = f'{grob.sektor.nazwa}/{grob.rzad}/{grob.numer}' if grob.rzad else f'{grob.sektor.nazwa}/{grob.numer}'
    return JsonResponse({'ok': True, 'tytul': tytul, 'id': grob.id})


def osoba_detail(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    osoba = get_object_or_404(Osoba.objects.select_related('grob', 'grob__sektor'), pk=pk)
    relacje = []
    for r in Relacja.objects.filter(Q(osoba_a=osoba) | Q(osoba_b=osoba)).select_related('osoba_a', 'osoba_b', 'osoba_a__grob__sektor', 'osoba_b__grob__sektor'):
        if r.osoba_a_id == osoba.pk:
            druga, kierunek = r.osoba_b, r.typ
        else:
            druga, kierunek = r.osoba_a, r.typ + '_zwrotna'
        relacje.append({'osoba': druga, 'typ': r.typ, 'kierunek': kierunek, 'etykieta': r.get_typ_display()})
    obserwuje = False
    if request.user.is_authenticated:
        obserwuje = osoba.obserwujacy.filter(user=request.user).exists()
    granica = timezone.now() - timedelta(hours=24)
    aktywne_swiece = osoba.swiece.filter(data_zapalenia__gte=granica)
    return render(request, 'groby/osoba_detail.html', {
        'osoba': osoba,
        'relacje': relacje,
        'obserwuje': obserwuje,
        'wspomnienia': osoba.wspomnienia.filter(status='zaakceptowane'),
        'liczba_swiec': aktywne_swiece.count(),
        'ostatnie_swiece': aktywne_swiece.order_by('-data_zapalenia')[:8],
    })


def _hash_ip(request):
    import hashlib
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
    return hashlib.sha256(ip.encode()).hexdigest()[:64]


@require_POST
def zapal_swiece(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    osoba = get_object_or_404(Osoba, pk=pk)
    if _antybot(request):
        return redirect('groby:osoba_detail', pk=pk)
    granica = timezone.now() - timedelta(minutes=10)
    iph = _hash_ip(request)
    if Swieca.objects.filter(osoba=osoba, ip_hash=iph, data_zapalenia__gte=granica).exists():
        messages.info(request, 'Już zapaliłeś świeczkę dla tej osoby. Spróbuj za chwilę.')
        return redirect('groby:osoba_detail', pk=pk)
    Swieca.objects.create(
        osoba=osoba,
        autor_user=request.user if request.user.is_authenticated else None,
        intencja=(request.POST.get('intencja') or '').strip()[:200],
        ip_hash=iph,
    )
    messages.success(request, 'Świeczka zapalona — pali się przez 24 godziny.')
    return redirect('groby:osoba_detail', pk=pk)


@require_POST
def dodaj_wspomnienie(request, pk):
    osoba = get_object_or_404(Osoba, pk=pk)
    if _antybot(request):
        messages.error(request, 'Wykryto podejrzaną aktywność.')
        return redirect('groby:osoba_detail', pk=pk)
    tresc = (request.POST.get('tresc') or '').strip()
    if not tresc:
        messages.error(request, 'Treść wspomnienia nie może być pusta.')
        return redirect('groby:osoba_detail', pk=pk)
    Wspomnienie.objects.create(
        osoba=osoba,
        autor_user=request.user if request.user.is_authenticated else None,
        autor_imie=(request.POST.get('autor_imie') or '').strip()[:100],
        tresc=tresc[:5000],
    )
    messages.success(request, 'Dziękujemy. Wspomnienie zostanie wyświetlone po akceptacji moderatora.')
    return redirect('groby:osoba_detail', pk=pk)


def kalendarz_rocznic(request):
    from datetime import date, timedelta
    dzis = date.today()
    okno = int(request.GET.get('dni', '30'))
    okno = max(7, min(okno, 365))
    osoby = Osoba.objects.exclude(data_smierci__isnull=True).select_related('grob__sektor')
    rocznice = []
    for o in osoby:
        try:
            rocznica = o.data_smierci.replace(year=dzis.year)
        except ValueError:
            rocznica = o.data_smierci.replace(year=dzis.year, day=28)
        if rocznica < dzis:
            try:
                rocznica = o.data_smierci.replace(year=dzis.year + 1)
            except ValueError:
                rocznica = o.data_smierci.replace(year=dzis.year + 1, day=28)
        delta = (rocznica - dzis).days
        if delta <= okno:
            lat = rocznica.year - o.data_smierci.year
            rocznice.append({
                'osoba': o,
                'data': rocznica,
                'za_dni': delta,
                'lat_temu': lat,
                'oryginal': o.data_smierci,
            })
    rocznice.sort(key=lambda r: r['za_dni'])
    return render(request, 'groby/kalendarz.html', {
        'rocznice': rocznice,
        'okno': okno,
        'dzis': dzis,
    })


def kalendarz_ical(request):
    from datetime import date, datetime, timedelta
    from django.utils import timezone
    dzis = date.today()
    okno = int(request.GET.get('dni', '90'))
    okno = max(7, min(okno, 365))
    osoby = Osoba.objects.exclude(data_smierci__isnull=True).select_related('grob__sektor')
    linie = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Informator Cmentarny Szydlow//PL',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:Rocznice śmierci — cmentarz w Szydłowie',
    ]
    for o in osoby:
        try:
            rocznica = o.data_smierci.replace(year=dzis.year)
        except ValueError:
            rocznica = o.data_smierci.replace(year=dzis.year, day=28)
        if rocznica < dzis:
            try:
                rocznica = o.data_smierci.replace(year=dzis.year + 1)
            except ValueError:
                rocznica = o.data_smierci.replace(year=dzis.year + 1, day=28)
        if (rocznica - dzis).days > okno:
            continue
        lat = rocznica.year - o.data_smierci.year
        uid = f'osoba-{o.pk}-{rocznica.strftime("%Y%m%d")}@cmentarz.szydlow'
        opis = f'{lat}. rocznica śmierci. Sektor {o.grob.sektor.nazwa}, grób {o.grob.numer}.'
        linie += [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{timezone.now().strftime("%Y%m%dT%H%M%SZ")}',
            f'DTSTART;VALUE=DATE:{rocznica.strftime("%Y%m%d")}',
            f'DTEND;VALUE=DATE:{(rocznica + timedelta(days=1)).strftime("%Y%m%d")}',
            f'SUMMARY:Rocznica śmierci — {o.imie} {o.nazwisko}',
            f'DESCRIPTION:{opis}',
            'END:VEVENT',
        ]
    linie.append('END:VCALENDAR')
    resp = HttpResponse('\r\n'.join(linie), content_type='text/calendar; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="rocznice.ics"'
    return resp


def drzewo(request, pk):
    osoba = get_object_or_404(Osoba.objects.select_related('grob__sektor'), pk=pk)
    rodzice, dzieci, malzonkowie, rodzenstwo = [], [], [], []
    for r in Relacja.objects.filter(Q(osoba_a=osoba) | Q(osoba_b=osoba)).select_related('osoba_a', 'osoba_b'):
        if r.typ == 'rodzic':
            if r.osoba_a_id == osoba.pk:
                dzieci.append(r.osoba_b)
            else:
                rodzice.append(r.osoba_a)
        elif r.typ == 'malzenstwo':
            malzonkowie.append(r.osoba_b if r.osoba_a_id == osoba.pk else r.osoba_a)
        elif r.typ == 'rodzenstwo':
            rodzenstwo.append(r.osoba_b if r.osoba_a_id == osoba.pk else r.osoba_a)
    return render(request, 'groby/drzewo.html', {
        'osoba': osoba,
        'rodzice': rodzice,
        'dzieci': dzieci,
        'malzonkowie': malzonkowie,
        'rodzenstwo': rodzenstwo,
    })


def eksport_csv(request):
    import csv
    osoby = _filtruj_osoby(request)[:5000]
    resp = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    resp['Content-Disposition'] = 'attachment; filename="osoby.csv"'
    resp.write('﻿')
    w = csv.writer(resp, delimiter=';')
    w.writerow(['Nazwisko', 'Imię', 'Drugie imię', 'Nazwisko rodowe', 'Data urodzenia', 'Data śmierci', 'Wiek', 'Sektor', 'Rząd', 'Numer grobu', 'Typ grobu'])
    for o in osoby:
        w.writerow([
            o.nazwisko, o.imie, o.drugie_imie, o.nazwisko_rodowe,
            o.data_urodzenia or '', o.data_smierci or '', o.wiek or '',
            o.grob.sektor.nazwa, o.grob.rzad, o.grob.numer, o.grob.get_typ_display(),
        ])
    return resp


def eksport_xlsx(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    osoby = _filtruj_osoby(request)[:10000]
    wb = Workbook()
    ws = wb.active
    ws.title = 'Osoby'
    naglowek = ['Nazwisko', 'Imię', 'Drugie imię', 'Nazwisko rodowe', 'Data urodzenia', 'Data śmierci', 'Wiek', 'Sektor', 'Rząd', 'Numer grobu', 'Typ grobu']
    ws.append(naglowek)
    fill = PatternFill(start_color='2E4430', end_color='2E4430', fill_type='solid')
    font = Font(color='FFFFFF', bold=True)
    for c in ws[1]:
        c.fill, c.font, c.alignment = fill, font, Alignment(horizontal='center')
    for o in osoby:
        ws.append([
            o.nazwisko, o.imie, o.drugie_imie, o.nazwisko_rodowe,
            o.data_urodzenia, o.data_smierci, o.wiek,
            o.grob.sektor.nazwa, o.grob.rzad, o.grob.numer, o.grob.get_typ_display(),
        ])
    for col_idx, szer in enumerate([18, 14, 12, 16, 13, 13, 6, 8, 6, 10, 14], start=1):
        ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = szer
    ws.freeze_panes = 'A2'
    buf = io.BytesIO()
    wb.save(buf)
    resp = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="osoby.xlsx"'
    return resp


def _filtruj_osoby(request):
    osoby = Osoba.objects.select_related('grob', 'grob__sektor')
    query = request.GET.get('q', '').strip()
    sektor_id = request.GET.get('sektor', '').strip()
    typ = request.GET.get('typ', '').strip()
    rok_od = request.GET.get('rok_od', '').strip()
    rok_do = request.GET.get('rok_do', '').strip()
    if query:
        osoby = _szukaj_fts(osoby, query)
    if sektor_id:
        osoby = osoby.filter(grob__sektor_id=sektor_id)
    if typ:
        osoby = osoby.filter(grob__typ=typ)
    if rok_od.isdigit():
        osoby = osoby.filter(data_smierci__year__gte=int(rok_od))
    if rok_do.isdigit():
        osoby = osoby.filter(data_smierci__year__lte=int(rok_do))
    return osoby.order_by('nazwisko', 'imie')


def indeks_nazwisk(request):
    nazwiska = (
        Osoba.objects.values('nazwisko')
        .annotate(n=Count('id'))
        .order_by('nazwisko')
    )
    grupy = defaultdict(list)
    for n in nazwiska:
        litera = (n['nazwisko'] or '?')[0].upper()
        if not litera.isalpha():
            litera = '#'
        grupy[litera].append({'nazwisko': n['nazwisko'], 'liczba': n['n']})
    grupy_lista = sorted(grupy.items())
    return render(request, 'groby/indeks_nazwisk.html', {
        'grupy': grupy_lista,
        'litery': [g[0] for g in grupy_lista],
        'razem': sum(n['n'] for n in nazwiska),
    })


def eksport_gedcom(request):
    """Eksport wszystkich osób + relacji do GEDCOM 5.5.5."""
    osoby = list(Osoba.objects.select_related('grob__sektor').all())
    relacje = list(Relacja.objects.select_related('osoba_a', 'osoba_b').all())

    # Pogrupuj relacje rodzic/małżeństwo na rodziny GEDCOM (FAM).
    # Dla każdej pary rodziców, wszystkie ich dzieci tworzą jedną FAM.
    # Małżeństwa bez wspólnych dzieci dostają własny FAM.
    rodzice_dziecka = defaultdict(list)  # dziecko_id -> [rodzice_ids]
    pary_malzonkow = set()
    for r in relacje:
        if r.typ == 'rodzic':
            rodzice_dziecka[r.osoba_b_id].append(r.osoba_a_id)
        elif r.typ == 'malzenstwo':
            para = tuple(sorted([r.osoba_a_id, r.osoba_b_id]))
            pary_malzonkow.add(para)

    rodziny = {}  # klucz: para rodziców (sorted) -> {ojciec, matka, dzieci}
    for dziecko_id, rodzice in rodzice_dziecka.items():
        klucz = tuple(sorted(rodzice))
        if klucz not in rodziny:
            rodziny[klucz] = {'rodzice': set(rodzice), 'dzieci': set()}
        rodziny[klucz]['dzieci'].add(dziecko_id)
    for para in pary_malzonkow:
        if para not in rodziny:
            rodziny[para] = {'rodzice': set(para), 'dzieci': set()}

    rodzina_indeks = {}  # klucz -> numer FAM
    for i, klucz in enumerate(rodziny.keys(), start=1):
        rodzina_indeks[klucz] = i

    # Mapowanie osoba -> FAMC (rodzina-z-rodzicow), FAMS (rodziny-malzeńskie)
    famc = defaultdict(list)
    fams = defaultdict(list)
    for klucz, dane in rodziny.items():
        idx = rodzina_indeks[klucz]
        for r in dane['rodzice']:
            fams[r].append(idx)
        for d in dane['dzieci']:
            famc[d].append(idx)

    linie = ['0 HEAD', '1 SOUR Informator-Cmentarny-Szydlow', '2 VERS 1.0',
             '1 GEDC', '2 VERS 5.5.5', '2 FORM LINEAGE-LINKED', '1 CHAR UTF-8']

    def gd_data(d):
        if not d:
            return None
        return d.strftime('%d %b %Y').upper()

    for o in osoby:
        linie.append(f'0 @I{o.pk}@ INDI')
        nazw = o.nazwisko_rodowe or o.nazwisko
        linie.append(f'1 NAME {o.imie} {o.drugie_imie} /{nazw}/'.replace('  ', ' ').strip())
        if o.imie:
            linie.append(f'2 GIVN {o.imie}{(" " + o.drugie_imie) if o.drugie_imie else ""}')
        if nazw:
            linie.append(f'2 SURN {nazw}')
        if o.data_urodzenia:
            linie.append('1 BIRT')
            linie.append(f'2 DATE {gd_data(o.data_urodzenia)}')
            if o.miejsce_urodzenia:
                linie.append(f'2 PLAC {o.miejsce_urodzenia}')
        if o.data_smierci:
            linie.append('1 DEAT')
            linie.append(f'2 DATE {gd_data(o.data_smierci)}')
            linie.append(f'2 PLAC Szydlow, sektor {o.grob.sektor.nazwa}, grob {o.grob.numer}')
        if o.biogram:
            linie.append(f'1 NOTE {o.biogram[:200]}')
        for f in famc[o.pk]:
            linie.append(f'1 FAMC @F{f}@')
        for f in fams[o.pk]:
            linie.append(f'1 FAMS @F{f}@')

    for klucz, dane in rodziny.items():
        idx = rodzina_indeks[klucz]
        linie.append(f'0 @F{idx}@ FAM')
        rodzice = sorted(dane['rodzice'])
        # Pierwsza osoba jako HUSB, druga jako WIFE (uproszczenie — bez płci w bazie)
        if rodzice:
            linie.append(f'1 HUSB @I{rodzice[0]}@')
        if len(rodzice) > 1:
            linie.append(f'1 WIFE @I{rodzice[1]}@')
        for d in sorted(dane['dzieci']):
            linie.append(f'1 CHIL @I{d}@')

    linie.append('0 TRLR')

    resp = HttpResponse('\r\n'.join(linie), content_type='application/x-gedcom; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="cmentarz-szydlow.ged"'
    return resp


def galeria_cmentarza(request):
    sektor_id = request.GET.get('sektor', '').strip()
    qs = Zdjecie.objects.select_related('grob__sektor').order_by('-data_dodania')
    if sektor_id:
        qs = qs.filter(grob__sektor_id=sektor_id)
    page = Paginator(qs, 60).get_page(request.GET.get('page'))
    return render(request, 'groby/galeria.html', {
        'page': page,
        'sektory': Sektor.objects.order_by('nazwa'),
        'sektor_id': sektor_id,
        'razem': qs.count(),
    })


@login_required
@require_POST
def zapisz_szukanie(request):
    nazwa = (request.POST.get('nazwa') or '').strip()[:100]
    querystring = (request.POST.get('querystring') or '').strip()[:500]
    if not nazwa or not querystring:
        messages.error(request, 'Wpisz nazwę.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    ZapisaneSzukanie.objects.create(user=request.user, nazwa=nazwa, querystring=querystring)
    messages.success(request, f'Zapisano: „{nazwa}"')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_POST
def usun_zapisane(request, pk):
    ZapisaneSzukanie.objects.filter(pk=pk, user=request.user).delete()
    return redirect('groby:profil')


def lista_wpisow(request):
    typ = request.GET.get('typ', '').strip()
    qs = Wpis.objects.filter(opublikowany=True).select_related('osoba__grob__sektor', 'autor')
    if typ:
        qs = qs.filter(typ=typ)
    return render(request, 'groby/wpisy_lista.html', {
        'wpisy': qs,
        'typ': typ,
        'typy': Wpis.TYP_CHOICES,
    })


def wpis_detail(request, slug):
    wpis = get_object_or_404(Wpis, slug=slug, opublikowany=True)
    return render(request, 'groby/wpis_detail.html', {'wpis': wpis})


def timeline(request):
    """Oś czasu: paski życia osób na linii czasu."""
    tag_slug = request.GET.get('tag', '').strip()
    qs = Osoba.objects.exclude(data_smierci__isnull=True).select_related('grob__sektor')
    if tag_slug:
        qs = qs.filter(tagi__slug=tag_slug)
    qs = qs.order_by('data_urodzenia', 'data_smierci')[:1000]
    osoby = []
    for o in qs:
        urodzony = o.data_urodzenia.year if o.data_urodzenia else (o.data_smierci.year - 70)
        zmarl = o.data_smierci.year
        osoby.append({
            'pk': o.pk, 'nazwa': f'{o.imie} {o.nazwisko}',
            'od': urodzony, 'do': zmarl, 'wiek': zmarl - urodzony,
            'sektor': o.grob.sektor.nazwa, 'numer': o.grob.numer,
        })
    return render(request, 'groby/timeline.html', {
        'dane_json': json.dumps(osoby, ensure_ascii=False),
        'wszystkie_tagi': Tag.objects.all(),
        'aktywny_tag': tag_slug,
    })


def widget(request, typ='szukaj'):
    """Uproszczone widoki bez nawigacji do osadzania w iframe innych stron."""
    osoby = []
    query = (request.GET.get('q') or '').strip()
    if query:
        osoby = list(_szukaj_fts(Osoba.objects.select_related('grob__sektor'), query)[:30])
    return render(request, 'groby/widget.html', {
        'osoby': osoby,
        'query': query,
    })


def health_check(request):
    """Endpoint dla monitoringu — zwraca JSON ze stanem systemu."""
    from django.db import connection
    import shutil
    stan = {'status': 'ok', 'checks': {}}
    try:
        with connection.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
        stan['checks']['database'] = 'ok'
    except Exception as e:
        stan['status'] = 'fail'
        stan['checks']['database'] = f'fail: {e}'
    try:
        usage = shutil.disk_usage('/')
        stan['checks']['disk_free_gb'] = round(usage.free / (1024**3), 2)
        if usage.free < 100 * 1024**2:  # < 100 MB
            stan['status'] = 'warn'
            stan['checks']['disk'] = 'warn: low space'
    except Exception:
        pass
    stan['liczby'] = {
        'sektory': Sektor.objects.count(),
        'groby': Grob.objects.count(),
        'osoby': Osoba.objects.count(),
        'zdjecia': Zdjecie.objects.count(),
    }
    return JsonResponse(stan, status=200 if stan['status'] == 'ok' else 503)


def szukaj_na_mapie(request):
    """API zwracające pasujące groby z pozycją na planie — dla wyszukiwarki na mapie."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'wyniki': []})
    osoby_ids = list(_szukaj_fts(Osoba.objects.values_list('pk', flat=True), q)[:50])
    groby = Grob.objects.filter(
        Q(osoby__pk__in=osoby_ids) | Q(numer__icontains=q),
        plan_x__isnull=False, plan_y__isnull=False,
    ).select_related('sektor').prefetch_related('osoby').distinct()[:30]
    wyniki = []
    for g in groby:
        osoby_str = ', '.join(f'{o.imie} {o.nazwisko}' for o in g.osoby.all()[:3])
        wyniki.append({
            'id': g.pk, 'x': g.plan_x, 'y': g.plan_y,
            'sektor': g.sektor.nazwa, 'numer': g.numer, 'rzad': g.rzad,
            'osoby': osoby_str or '—',
            'url': reverse('groby:grob_detail', args=[g.pk]),
        })
    return JsonResponse({'wyniki': wyniki})


def lista_panoram(request):
    panoramy = Panorama.objects.select_related('sektor').order_by('kolejnosc', 'nazwa')
    return render(request, 'groby/panoramy_lista.html', {'panoramy': panoramy})


def panorama_detail(request, pk):
    panorama = get_object_or_404(Panorama.objects.prefetch_related('hotspoty__grob__sektor'), pk=pk)
    return render(request, 'groby/panorama_detail.html', {'panorama': panorama})


# ---- Magic link ----

def magic_link_zarzadaj(request):
    if request.method != 'POST':
        return render(request, 'groby/magic_link.html')
    email = (request.POST.get('email') or '').strip()
    if not email:
        messages.error(request, 'Podaj adres e-mail.')
        return redirect('groby:magic_link')
    User = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    if user:
        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from django.core.mail import send_mail
        from django.conf import settings
        token = secrets.token_urlsafe(32)
        TokenLogowania.objects.create(
            user=user, token=token,
            data_wygasniecia=timezone.now() + timedelta(minutes=30),
        )
        link = request.build_absolute_uri(reverse('groby:magic_link_uzyj', args=[token]))
        send_mail(
            'Logowanie do Informatora Cmentarnego',
            f'Kliknij aby się zalogować: {link}\nLink wygaśnie za 30 minut.\n',
            settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True,
        )
    messages.success(request, 'Jeśli ten e-mail jest zarejestrowany, link został wysłany.')
    return redirect('groby:magic_link')


def magic_link_uzyj(request, token):
    from django.utils import timezone
    t = TokenLogowania.objects.filter(token=token, wykorzystany=False).first()
    if not t or t.data_wygasniecia < timezone.now():
        messages.error(request, 'Link nieaktualny lub już użyty. Wygeneruj nowy.')
        return redirect('groby:magic_link')
    t.wykorzystany = True
    t.save(update_fields=['wykorzystany'])
    login(request, t.user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f'Zalogowano jako {t.user.username}.')
    return redirect('groby:profil')


# ---- 2FA TOTP ----

@login_required
def totp_setup(request):
    """Konfiguracja 2FA: generuje sekret, pokazuje QR; potwierdzenie kodem aktywuje urządzenie."""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    import qrcode, base64
    device = TOTPDevice.objects.filter(user=request.user, name='default').first()

    if request.method == 'POST':
        kod = (request.POST.get('kod') or '').strip()
        if device and device.verify_token(kod):
            device.confirmed = True
            device.save()
            messages.success(request, '2FA aktywne.')
            return redirect('groby:profil')
        messages.error(request, 'Kod nieprawidłowy.')

    if not device:
        device = TOTPDevice.objects.create(user=request.user, name='default', confirmed=False)
    config_url = device.config_url
    img = qrcode.make(config_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render(request, 'groby/totp_setup.html', {
        'device': device, 'qr_b64': qr_b64, 'config_url': config_url,
    })


@login_required
@require_POST
def totp_wylacz(request):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    TOTPDevice.objects.filter(user=request.user).delete()
    messages.success(request, '2FA wyłączone.')
    return redirect('groby:profil')


# ---- Web Push ----

def push_klucz_publiczny(request):
    """Zwraca klucz publiczny VAPID (frontend potrzebuje do subscribe())."""
    from django.conf import settings
    return JsonResponse({'publicKey': getattr(settings, 'VAPID_PUBLIC_KEY', '')})


@require_POST
def push_subskrybuj(request):
    try:
        data = json.loads(request.body or '{}')
        endpoint = data['endpoint']
        keys = data.get('keys', {})
        SubskrypcjaPush.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'p256dh': keys.get('p256dh', '')[:200],
                'auth': keys.get('auth', '')[:80],
                'user': request.user if request.user.is_authenticated else None,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
            },
        )
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({'ok': False}, status=400)
    return JsonResponse({'ok': True})


# ---- Bulk import zdjęć ZIP ----

@login_required
def bulk_import_zdjec(request):
    if not request.user.is_staff:
        return redirect('admin:login')
    raport = None
    if request.method == 'POST' and request.FILES.get('zip'):
        import zipfile, re, os
        from django.core.files.base import ContentFile
        plik = request.FILES['zip']
        dodanych, pominietych, bledow = 0, 0, []
        try:
            with zipfile.ZipFile(plik) as zf:
                for nazwa in zf.namelist():
                    if nazwa.endswith('/') or not re.search(r'\.(jpe?g|png|webp)$', nazwa, re.I):
                        continue
                    base = os.path.basename(nazwa)
                    # Wzorzec: SEKTOR_NUMER[_KOL].ext  np. A_12.jpg, B_5_2.jpg
                    m = re.match(r'^([A-Za-z0-9]+)[_-]([A-Za-z0-9]+)(?:[_-](\d+))?\..+$', base)
                    if not m:
                        bledow.append(f'{base}: nie pasuje wzorzec SEKTOR_NUMER.jpg')
                        continue
                    sektor_n, numer, kol = m.group(1), m.group(2), int(m.group(3) or 0)
                    grob = Grob.objects.filter(sektor__nazwa__iexact=sektor_n, numer=numer).first()
                    if not grob:
                        pominietych += 1
                        bledow.append(f'{base}: brak grobu {sektor_n}/{numer}')
                        continue
                    z = Zdjecie(grob=grob, kolejnosc=kol)
                    z.plik.save(base, ContentFile(zf.read(nazwa)), save=True)
                    dodanych += 1
            raport = {'dodanych': dodanych, 'pominietych': pominietych, 'bledow': bledow[:30]}
        except zipfile.BadZipFile:
            messages.error(request, 'Nieprawidłowy plik ZIP.')
    return render(request, 'groby/bulk_import.html', {'raport': raport})


def manifest(request):
    data = {
        "name": "Informator Cmentarny — Szydłów",
        "short_name": "Szydłów",
        "description": "Cmentarz parafialny w Szydłowie — wyszukiwarka grobów.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#fbf9f4",
        "theme_color": "#2e4430",
        "lang": "pl",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    return JsonResponse(data)


def service_worker(request):
    sw = """
const CACHE = 'groby-v1';
const ASSETY = ['/', '/szukaj/', '/sektory/', '/o-cmentarzu/', '/manifest.webmanifest'];
self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETY)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
    e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
    if (e.request.method !== 'GET') return;
    const u = new URL(e.request.url);
    if (u.pathname.startsWith('/admin') || u.pathname.startsWith('/staff') || u.pathname.startsWith('/api')) return;
    e.respondWith(
        caches.match(e.request).then(c => c || fetch(e.request).then(r => {
            if (r.ok && (r.type === 'basic' || r.type === 'cors')) {
                const kopia = r.clone();
                caches.open(CACHE).then(cc => cc.put(e.request, kopia));
            }
            return r;
        }).catch(() => caches.match('/')))
    );
});
"""
    return HttpResponse(sw, content_type='application/javascript')


def grob_qr(request, pk):
    import qrcode
    grob = get_object_or_404(Grob, pk=pk)
    url = request.build_absolute_uri(reverse('groby:grob_detail', args=[grob.pk]))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return HttpResponse(buf.getvalue(), content_type='image/png')


def qr_naklejki(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect('admin:login')
    sektor_id = request.GET.get('sektor', '').strip()
    qs = Grob.objects.select_related('sektor').order_by('sektor__nazwa', 'rzad', 'numer')
    if sektor_id:
        qs = qs.filter(sektor_id=sektor_id)
    return render(request, 'groby/qr_naklejki.html', {
        'groby': qs,
        'sektory': Sektor.objects.order_by('nazwa'),
        'wybrany_sektor': sektor_id,
    })


def zglos_poprawke(request, cel, pk):
    if request.method != 'POST':
        return redirect('groby:home')
    if _antybot(request):
        messages.error(request, 'Wykryto podejrzaną aktywność. Spróbuj ponownie.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    tresc = (request.POST.get('tresc') or '').strip()
    if not tresc:
        messages.error(request, 'Treść zgłoszenia nie może być pusta.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    autor_imie = (request.POST.get('autor_imie') or '').strip()[:100]
    autor_email = (request.POST.get('autor_email') or '').strip()[:200]
    z = Zgloszenie(
        tresc=tresc,
        autor_imie=autor_imie,
        autor_email=autor_email,
        autor_user=request.user if request.user.is_authenticated else None,
    )
    if cel == 'grob':
        z.grob = get_object_or_404(Grob, pk=pk)
    elif cel == 'osoba':
        z.osoba = get_object_or_404(Osoba, pk=pk)
    else:
        return redirect('groby:home')
    z.save()
    messages.success(request, 'Dziękujemy! Zgłoszenie zostało zarejestrowane.')
    return redirect(request.META.get('HTTP_REFERER', '/'))


def eksport_pdf(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from pathlib import Path

    osoby = Osoba.objects.select_related('grob', 'grob__sektor')
    query = request.GET.get('q', '').strip()
    sektor_id = request.GET.get('sektor', '').strip()
    typ = request.GET.get('typ', '').strip()
    rok_od = request.GET.get('rok_od', '').strip()
    rok_do = request.GET.get('rok_do', '').strip()
    if query:
        osoby = osoby.filter(Q(nazwisko__icontains=query) | Q(imie__icontains=query) | Q(nazwisko_rodowe__icontains=query))
    if sektor_id:
        osoby = osoby.filter(grob__sektor_id=sektor_id)
    if typ:
        osoby = osoby.filter(grob__typ=typ)
    if rok_od.isdigit():
        osoby = osoby.filter(data_smierci__year__gte=int(rok_od))
    if rok_do.isdigit():
        osoby = osoby.filter(data_smierci__year__lte=int(rok_do))
    osoby = osoby.order_by('nazwisko', 'imie')[:2000]

    czcionka_nazwa = 'Helvetica'
    for kandydat in (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\calibri.ttf'):
        if Path(kandydat).exists():
            try:
                pdfmetrics.registerFont(TTFont('Polska', kandydat))
                czcionka_nazwa = 'Polska'
                break
            except Exception:
                pass

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    style_h1 = ParagraphStyle('h1', fontName=czcionka_nazwa, fontSize=18, leading=22, spaceAfter=6)
    style_meta = ParagraphStyle('meta', fontName=czcionka_nazwa, fontSize=9, textColor=colors.grey, spaceAfter=12)
    style_n = ParagraphStyle('n', fontName=czcionka_nazwa, fontSize=9, leading=11)
    elementy = []
    elementy.append(Paragraph('Księga zmarłych — cmentarz w Szydłowie', style_h1))
    filtry = []
    if query: filtry.append(f'fraza: „{query}"')
    if sektor_id: filtry.append(f'sektor: {Sektor.objects.filter(pk=sektor_id).values_list("nazwa", flat=True).first() or "?"}')
    if typ: filtry.append(f'typ: {dict(Grob.TYP_CHOICES).get(typ, typ)}')
    if rok_od: filtry.append(f'od {rok_od}')
    if rok_do: filtry.append(f'do {rok_do}')
    elementy.append(Paragraph('Filtry: ' + ('; '.join(filtry) if filtry else 'brak') + f'.   Wyników: {len(osoby)}.', style_meta))

    naglowek = ['Lp.', 'Nazwisko i imię', 'Daty', 'Lokalizacja']
    dane = [naglowek]
    for i, o in enumerate(osoby, start=1):
        nazwa = f'{o.nazwisko} {o.imie}'
        if o.nazwisko_rodowe:
            nazwa += f' (z d. {o.nazwisko_rodowe})'
        ur = o.data_urodzenia.strftime('%Y-%m-%d') if o.data_urodzenia else '?'
        sm = o.data_smierci.strftime('%Y-%m-%d') if o.data_smierci else '?'
        lok = f'sekt. {o.grob.sektor.nazwa}'
        if o.grob.rzad:
            lok += f', rz. {o.grob.rzad}'
        lok += f', nr {o.grob.numer}'
        dane.append([
            Paragraph(str(i), style_n),
            Paragraph(nazwa, style_n),
            Paragraph(f'{ur} — {sm}', style_n),
            Paragraph(lok, style_n),
        ])
    tab = Table(dane, colWidths=[1.0 * cm, 7.5 * cm, 4.0 * cm, 5.0 * cm], repeatRows=1)
    tab.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), czcionka_nazwa),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e4430')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f6ef')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementy.append(tab)
    doc.build(elementy)
    buf.seek(0)
    resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="ksiega-zmarlych.pdf"'
    return resp


def rejestracja(request):
    if request.user.is_authenticated:
        return redirect('groby:profil')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profil.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Konto utworzone.')
            return redirect('groby:profil')
    else:
        form = UserCreationForm()
    return render(request, 'groby/rejestracja.html', {'form': form})


@login_required
def profil(request):
    profil_obj, _ = Profil.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        profil_obj.pokrewienstwo = (request.POST.get('pokrewienstwo') or '').strip()[:200]
        profil_obj.save(update_fields=['pokrewienstwo'])
        messages.success(request, 'Profil zapisany.')
        return redirect('groby:profil')
    return render(request, 'groby/profil.html', {
        'profil': profil_obj,
        'obserwowane_groby': profil_obj.obserwowane_groby.select_related('sektor').prefetch_related('osoby'),
        'obserwowane_osoby': profil_obj.obserwowane_osoby.select_related('grob__sektor'),
        'moje_zgloszenia': Zgloszenie.objects.filter(autor_user=request.user).select_related('grob__sektor', 'osoba__grob__sektor')[:20],
        'zapisane_szukania': request.user.zapisane_szukania.all()[:20],
    })


@login_required
@require_POST
def przelacz_obserwacje(request, cel, pk):
    profil_obj, _ = Profil.objects.get_or_create(user=request.user)
    if cel == 'grob':
        obj = get_object_or_404(Grob, pk=pk)
        if profil_obj.obserwowane_groby.filter(pk=obj.pk).exists():
            profil_obj.obserwowane_groby.remove(obj)
        else:
            profil_obj.obserwowane_groby.add(obj)
    elif cel == 'osoba':
        obj = get_object_or_404(Osoba, pk=pk)
        if profil_obj.obserwowane_osoby.filter(pk=obj.pk).exists():
            profil_obj.obserwowane_osoby.remove(obj)
        else:
            profil_obj.obserwowane_osoby.add(obj)
    return redirect(request.META.get('HTTP_REFERER', '/'))


def dashboard_staff(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect('admin:login')
    metryki = {
        'zgloszenia_nowe': Zgloszenie.objects.filter(status='nowe').count(),
        'wspomnienia_oczekujace': Wspomnienie.objects.filter(status='oczekuje').count(),
        'groby_bez_pozycji': Grob.objects.filter(plan_x__isnull=True).count(),
        'groby_bez_osob': Grob.objects.annotate(_n=Count('osoby')).filter(_n=0).count(),
        'osoby_bez_dat': Osoba.objects.filter(data_smierci__isnull=True).count(),
        'liczba_zdjec': Zdjecie.objects.count(),
        'aktywne_swiece_24h': Swieca.objects.filter(data_zapalenia__gte=_now_minus_hours(24)).count(),
        'liczba_userow': __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model().objects.count(),
        'ostatnie_zmiany': HistoriaZmian.objects.select_related('user').order_by('-data')[:10],
        'najnowsze_zgloszenia': Zgloszenie.objects.select_related('grob__sektor', 'osoba').order_by('-data_dodania')[:5],
        'najnowsze_wspomnienia': Wspomnienie.objects.filter(status='oczekuje').select_related('osoba')[:5],
    }
    return render(request, 'groby/dashboard.html', metryki)


def _now_minus_hours(h):
    from datetime import timedelta
    from django.utils import timezone
    return timezone.now() - timedelta(hours=h)


def duplikaty(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect('admin:login')
    klucze = defaultdict(list)
    for o in Osoba.objects.select_related('grob__sektor').all():
        klucz = (o.imie.lower().strip(), o.nazwisko.lower().strip(),
                 o.data_smierci.year if o.data_smierci else None)
        klucze[klucz].append(o)
    grupy = []
    for klucz, lista in klucze.items():
        if len(lista) > 1:
            grupy.append({
                'imie': klucz[0].title(),
                'nazwisko': klucz[1].title(),
                'rok': klucz[2],
                'osoby': sorted(lista, key=lambda o: o.pk),
            })
    grupy.sort(key=lambda g: (g['nazwisko'], g['imie']))
    return render(request, 'groby/duplikaty.html', {
        'grupy': grupy,
    })


def historia_zmian(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect('admin:login')
    qs = HistoriaZmian.objects.select_related('user').order_by('-data')
    model = request.GET.get('model', '').strip()
    if model:
        qs = qs.filter(model=model)
    page = Paginator(qs, 50).get_page(request.GET.get('page'))
    return render(request, 'groby/historia.html', {
        'page': page,
        'model_filtr': model,
    })
