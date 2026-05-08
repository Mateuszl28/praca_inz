from django.contrib import admin
from .models import (
    Sektor, Grob, Osoba, Zdjecie, Relacja, Zgloszenie, Profil, HistoriaZmian,
    Wspomnienie, Swieca, ZapisaneSzukanie, Wpis,
    Tag, Panorama, HotspotPanoramy, SubskrypcjaPush, TokenLogowania,
)


admin.site.site_header = 'Informator Cmentarny — Szydłów'
admin.site.site_title = 'Panel administracyjny'
admin.site.index_title = 'Zarządzanie danymi'


class OsobaInline(admin.TabularInline):
    model = Osoba
    extra = 1
    fields = ('imie', 'nazwisko', 'nazwisko_rodowe', 'data_urodzenia', 'data_smierci')


class ZdjecieInline(admin.TabularInline):
    model = Zdjecie
    extra = 1
    fields = ('plik', 'podpis', 'kolejnosc')


@admin.register(Sektor)
class SektorAdmin(admin.ModelAdmin):
    list_display = ('nazwa', 'liczba_grobow')
    search_fields = ('nazwa',)

    @admin.display(description='Liczba grobów')
    def liczba_grobow(self, obj):
        return obj.groby.count()


@admin.register(Grob)
class GrobAdmin(admin.ModelAdmin):
    list_display = ('sektor', 'numer', 'rzad', 'typ', 'liczba_osob', 'data_modyfikacji')
    list_filter = ('sektor', 'typ')
    search_fields = ('numer', 'sektor__nazwa', 'osoby__nazwisko', 'osoby__imie')
    inlines = [OsobaInline, ZdjecieInline]
    readonly_fields = ('data_dodania', 'data_modyfikacji')
    fieldsets = (
        ('Lokalizacja', {'fields': ('sektor', 'numer', 'rzad', 'typ')}),
        ('Współrzędne na mapie', {'fields': ('szerokosc_geo', 'dlugosc_geo'), 'classes': ('collapse',)}),
        ('Dodatkowe', {'fields': ('zdjecie', 'uwagi')}),
        ('Metadane', {'fields': ('data_dodania', 'data_modyfikacji'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Liczba osób')
    def liczba_osob(self, obj):
        return obj.osoby.count()


@admin.register(Osoba)
class OsobaAdmin(admin.ModelAdmin):
    list_display = ('nazwisko', 'imie', 'data_urodzenia', 'data_smierci', 'grob')
    list_filter = ('grob__sektor',)
    search_fields = ('nazwisko', 'imie', 'nazwisko_rodowe')
    date_hierarchy = 'data_smierci'
    autocomplete_fields = ('grob',)
    fieldsets = (
        ('Dane osobowe', {'fields': ('imie', 'drugie_imie', 'nazwisko', 'nazwisko_rodowe')}),
        ('Daty', {'fields': ('data_urodzenia', 'data_smierci', 'miejsce_urodzenia')}),
        ('Grób', {'fields': ('grob',)}),
        ('Biogram', {'fields': ('biogram',)}),
    )


@admin.register(Zdjecie)
class ZdjecieAdmin(admin.ModelAdmin):
    list_display = ('grob', 'podpis', 'kolejnosc', 'data_dodania')
    list_filter = ('grob__sektor',)
    search_fields = ('grob__numer', 'podpis')
    autocomplete_fields = ('grob',)


@admin.register(Relacja)
class RelacjaAdmin(admin.ModelAdmin):
    list_display = ('osoba_a', 'typ', 'osoba_b')
    list_filter = ('typ',)
    autocomplete_fields = ('osoba_a', 'osoba_b')
    search_fields = ('osoba_a__nazwisko', 'osoba_b__nazwisko')


@admin.register(Zgloszenie)
class ZgloszenieAdmin(admin.ModelAdmin):
    list_display = ('id', 'cel_str', 'autor_imie', 'status', 'data_dodania')
    list_filter = ('status', 'typ')
    search_fields = ('tresc', 'autor_imie', 'autor_email')
    readonly_fields = ('data_dodania', 'data_modyfikacji', 'autor_user')
    autocomplete_fields = ('grob', 'osoba')
    fieldsets = (
        ('Cel zgłoszenia', {'fields': ('grob', 'osoba')}),
        ('Treść', {'fields': ('typ', 'tresc')}),
        ('Autor', {'fields': ('autor_imie', 'autor_email', 'autor_user')}),
        ('Moderacja', {'fields': ('status', 'odpowiedz')}),
        ('Metadane', {'fields': ('data_dodania', 'data_modyfikacji'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Cel')
    def cel_str(self, obj):
        if obj.osoba:
            return f'Osoba: {obj.osoba}'
        if obj.grob:
            return f'Grób: {obj.grob}'
        return '—'


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'pokrewienstwo', 'data_utworzenia')
    search_fields = ('user__username', 'user__email', 'pokrewienstwo')
    filter_horizontal = ('obserwowane_groby', 'obserwowane_osoby')


@admin.register(Wspomnienie)
class WspomnienieAdmin(admin.ModelAdmin):
    list_display = ('osoba', 'autor_str', 'status', 'data_dodania')
    list_filter = ('status',)
    search_fields = ('tresc', 'autor_imie', 'osoba__nazwisko')
    autocomplete_fields = ('osoba',)
    actions = ['zaakceptuj', 'odrzuc']
    readonly_fields = ('data_dodania', 'autor_user')

    @admin.action(description='Zaakceptuj wybrane wspomnienia')
    def zaakceptuj(self, request, queryset):
        for w in queryset:
            w.status = 'zaakceptowane'
            w.save()

    @admin.action(description='Odrzuć wybrane wspomnienia')
    def odrzuc(self, request, queryset):
        queryset.update(status='odrzucone')


@admin.register(Swieca)
class SwiecaAdmin(admin.ModelAdmin):
    list_display = ('osoba', 'intencja', 'autor_user', 'data_zapalenia')
    search_fields = ('osoba__nazwisko', 'intencja')
    readonly_fields = ('ip_hash', 'data_zapalenia')


@admin.register(Wpis)
class WpisAdmin(admin.ModelAdmin):
    list_display = ('tytul', 'typ', 'opublikowany', 'data_publikacji', 'autor')
    list_filter = ('typ', 'opublikowany')
    search_fields = ('tytul', 'tresc', 'podpis')
    prepopulated_fields = {'slug': ('tytul',)}
    autocomplete_fields = ('osoba',)
    readonly_fields = ('data_dodania', 'data_modyfikacji')

    def save_model(self, request, obj, form, change):
        if not obj.autor_id:
            obj.autor = request.user
        super().save_model(request, obj, form, change)


@admin.register(ZapisaneSzukanie)
class ZapisaneSzukanieAdmin(admin.ModelAdmin):
    list_display = ('nazwa', 'user', 'querystring', 'data_utworzenia')
    search_fields = ('nazwa', 'user__username')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('nazwa', 'slug', 'liczba_osob')
    search_fields = ('nazwa',)
    prepopulated_fields = {'slug': ('nazwa',)}
    filter_horizontal = ('osoby',)

    @admin.display(description='Osób')
    def liczba_osob(self, obj):
        return obj.osoby.count()


class HotspotInline(admin.TabularInline):
    model = HotspotPanoramy
    extra = 1
    fk_name = 'panorama'
    fields = ('pitch', 'yaw', 'etykieta', 'grob', 'docelowa_panorama')


@admin.register(Panorama)
class PanoramaAdmin(admin.ModelAdmin):
    list_display = ('nazwa', 'sektor', 'kolejnosc')
    list_filter = ('sektor',)
    search_fields = ('nazwa', 'opis')
    inlines = [HotspotInline]


@admin.register(SubskrypcjaPush)
class SubskrypcjaPushAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'data_dodania', 'user_agent')
    readonly_fields = ('endpoint', 'p256dh', 'auth', 'user_agent', 'data_dodania')


@admin.register(TokenLogowania)
class TokenLogowaniaAdmin(admin.ModelAdmin):
    list_display = ('user', 'wykorzystany', 'data_utworzenia', 'data_wygasniecia')
    list_filter = ('wykorzystany',)
    readonly_fields = ('token', 'data_utworzenia')


@admin.register(HistoriaZmian)
class HistoriaZmianAdmin(admin.ModelAdmin):
    list_display = ('data', 'akcja', 'model', 'obiekt_repr', 'user')
    list_filter = ('akcja', 'model')
    search_fields = ('obiekt_repr',)
    readonly_fields = ('model', 'obiekt_id', 'obiekt_repr', 'akcja', 'pola', 'user', 'data')
    date_hierarchy = 'data'
