"""REST API dla informatora cmentarnego.

Domyślnie API jest tylko-do-odczytu dla anonimowych użytkowników; pisanie
wymaga zalogowania (sesja Django lub Basic Auth). Endpointy:

    /api/v1/sektory/
    /api/v1/groby/
    /api/v1/osoby/
"""
from django.urls import include, path
from rest_framework import serializers, viewsets, routers
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Sektor, Grob, Osoba


class SektorSerializer(serializers.ModelSerializer):
    liczba_grobow = serializers.IntegerField(source='groby.count', read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='sektor-detail')

    class Meta:
        model = Sektor
        fields = ['id', 'url', 'nazwa', 'opis', 'liczba_grobow']


class OsobaKrotki(serializers.ModelSerializer):
    """Lekka reprezentacja osoby do osadzenia w grobach."""
    class Meta:
        model = Osoba
        fields = ['id', 'imie', 'nazwisko', 'nazwisko_rodowe', 'data_urodzenia', 'data_smierci']


class GrobSerializer(serializers.ModelSerializer):
    sektor = serializers.SlugRelatedField(slug_field='nazwa', queryset=Sektor.objects.all())
    osoby = OsobaKrotki(many=True, read_only=True)
    typ_etykieta = serializers.CharField(source='get_typ_display', read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='grob-detail')
    strona_html = serializers.SerializerMethodField()

    class Meta:
        model = Grob
        fields = [
            'id', 'url', 'sektor', 'rzad', 'numer', 'typ', 'typ_etykieta',
            'plan_x', 'plan_y', 'szerokosc_geo', 'dlugosc_geo',
            'osoby', 'strona_html',
        ]

    def get_strona_html(self, obj):
        return self.context['request'].build_absolute_uri(f'/grob/{obj.pk}/')


class OsobaSerializer(serializers.ModelSerializer):
    grob_id = serializers.PrimaryKeyRelatedField(source='grob', queryset=Grob.objects.all())
    sektor = serializers.CharField(source='grob.sektor.nazwa', read_only=True)
    numer_grobu = serializers.CharField(source='grob.numer', read_only=True)
    wiek = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='osoba-detail')
    strona_html = serializers.SerializerMethodField()

    class Meta:
        model = Osoba
        fields = [
            'id', 'url', 'imie', 'drugie_imie', 'nazwisko', 'nazwisko_rodowe',
            'data_urodzenia', 'data_smierci', 'wiek', 'miejsce_urodzenia',
            'biogram', 'grob_id', 'sektor', 'numer_grobu', 'strona_html',
        ]

    def get_strona_html(self, obj):
        return self.context['request'].build_absolute_uri(f'/osoba/{obj.pk}/')


class SektorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sektor.objects.all().order_by('nazwa')
    serializer_class = SektorSerializer
    search_fields = ['nazwa']

    @action(detail=True)
    def groby(self, request, pk=None):
        """Lista grobów w sektorze."""
        groby = Grob.objects.filter(sektor_id=pk).order_by('rzad', 'numer')
        page = self.paginate_queryset(groby)
        ser = GrobSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(ser.data)


class GrobViewSet(viewsets.ModelViewSet):
    queryset = Grob.objects.select_related('sektor').prefetch_related('osoby')
    serializer_class = GrobSerializer
    filterset_fields = ['sektor', 'typ', 'rzad']
    search_fields = ['numer', 'sektor__nazwa', 'osoby__nazwisko']
    ordering_fields = ['sektor__nazwa', 'rzad', 'numer', 'data_modyfikacji']


class OsobaViewSet(viewsets.ModelViewSet):
    queryset = Osoba.objects.select_related('grob__sektor')
    serializer_class = OsobaSerializer
    filterset_fields = ['grob__sektor', 'grob__typ']
    search_fields = ['nazwisko', 'imie', 'nazwisko_rodowe']
    ordering_fields = ['nazwisko', 'imie', 'data_urodzenia', 'data_smierci']


router = routers.DefaultRouter()
router.register(r'sektory', SektorViewSet)
router.register(r'groby', GrobViewSet)
router.register(r'osoby', OsobaViewSet)


urlpatterns = [
    path('v1/', include(router.urls)),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]
