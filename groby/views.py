from django.shortcuts import render, get_object_or_404
from django.db.models import Q
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
    wyniki = []
    if query:
        wyniki = Osoba.objects.filter(
            Q(nazwisko__icontains=query)
            | Q(imie__icontains=query)
            | Q(nazwisko_rodowe__icontains=query)
        ).select_related('grob', 'grob__sektor').order_by('nazwisko', 'imie')
    return render(request, 'groby/szukaj.html', {'query': query, 'wyniki': wyniki})


def grob_detail(request, pk):
    grob = get_object_or_404(Grob.objects.select_related('sektor').prefetch_related('osoby'), pk=pk)
    return render(request, 'groby/grob_detail.html', {'grob': grob})


def osoba_detail(request, pk):
    osoba = get_object_or_404(Osoba.objects.select_related('grob', 'grob__sektor'), pk=pk)
    return render(request, 'groby/osoba_detail.html', {'osoba': osoba})
