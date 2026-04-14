from django.contrib import admin
from .models import Sektor, Grob, Osoba


admin.site.site_header = 'Informator Cmentarny — Szydłów'
admin.site.site_title = 'Panel administracyjny'
admin.site.index_title = 'Zarządzanie danymi'


class OsobaInline(admin.TabularInline):
    model = Osoba
    extra = 1
    fields = ('imie', 'nazwisko', 'nazwisko_rodowe', 'data_urodzenia', 'data_smierci')


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
    inlines = [OsobaInline]
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
