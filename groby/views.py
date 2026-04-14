from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Osoba, Grob, Sektor


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


def osoba_detail(request, pk):
    osoba = get_object_or_404(Osoba.objects.select_related('grob', 'grob__sektor'), pk=pk)
    return render(request, 'groby/osoba_detail.html', {'osoba': osoba})
