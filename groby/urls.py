from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'groby'

urlpatterns = [
    path('', views.home, name='home'),
    path('szukaj/', views.szukaj, name='szukaj'),
    path('szukaj/pdf/', views.eksport_pdf, name='eksport_pdf'),
    path('mapa/', views.mapa, name='mapa'),
    path('statystyki/', views.statystyki, name='statystyki'),
    path('o-cmentarzu/', views.o_cmentarzu, name='o_cmentarzu'),
    path('api/sugestie/', views.sugestie, name='sugestie'),
    path('sektory/', views.sektory_list, name='sektory_list'),
    path('sektor/<int:pk>/', views.sektor_detail, name='sektor_detail'),
    path('grob/<int:pk>/', views.grob_detail, name='grob_detail'),
    path('grob/<int:pk>/qr.png', views.grob_qr, name='grob_qr'),
    path('osoba/<int:pk>/', views.osoba_detail, name='osoba_detail'),
    path('osoba/<int:pk>/drzewo/', views.drzewo, name='drzewo'),
    path('osoba/<int:pk>/swieca/', views.zapal_swiece, name='zapal_swiece'),
    path('osoba/<int:pk>/wspomnienie/', views.dodaj_wspomnienie, name='dodaj_wspomnienie'),
    path('kalendarz/', views.kalendarz_rocznic, name='kalendarz'),
    path('kalendarz.ics', views.kalendarz_ical, name='kalendarz_ical'),
    path('indeks/', views.indeks_nazwisk, name='indeks'),
    path('szukaj/csv/', views.eksport_csv, name='eksport_csv'),
    path('szukaj/xlsx/', views.eksport_xlsx, name='eksport_xlsx'),
    path('eksport.ged', views.eksport_gedcom, name='eksport_gedcom'),
    path('galeria/', views.galeria_cmentarza, name='galeria_cmentarza'),
    path('postacie/', views.lista_wpisow, name='wpisy_lista'),
    path('postacie/<slug:slug>/', views.wpis_detail, name='wpis_detail'),
    path('zapisz-szukanie/', views.zapisz_szukanie, name='zapisz_szukanie'),
    path('zapisane/<int:pk>/usun/', views.usun_zapisane, name='usun_zapisane'),
    path('manifest.webmanifest', views.manifest, name='manifest'),
    path('sw.js', views.service_worker, name='sw'),
    path('api/zapisz-pozycje/', views.zapisz_pozycje, name='zapisz_pozycje'),

    # Zgłoszenia poprawek
    path('zglos/<str:cel>/<int:pk>/', views.zglos_poprawke, name='zglos_poprawke'),

    # Panel staffu
    path('staff/', views.dashboard_staff, name='dashboard'),
    path('staff/qr-naklejki/', views.qr_naklejki, name='qr_naklejki'),
    path('staff/historia/', views.historia_zmian, name='historia'),
    path('staff/duplikaty/', views.duplikaty, name='duplikaty'),

    # Konta użytkowników
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path('logowanie/', auth_views.LoginView.as_view(template_name='groby/logowanie.html'), name='logowanie'),
    path('wylogowanie/', auth_views.LogoutView.as_view(), name='wylogowanie'),
    path('profil/', views.profil, name='profil'),
    path('obserwuj/<str:cel>/<int:pk>/', views.przelacz_obserwacje, name='przelacz_obserwacje'),
]
