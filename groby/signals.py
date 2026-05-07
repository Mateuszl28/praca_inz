"""Sygnały Django -> wpisy do HistoriaZmian dla Grob i Osoba.

Bieżący użytkownik jest pobierany z thread-local (ustawianego przez middleware).
"""
import threading
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Grob, Osoba, Zdjecie, Wspomnienie, Zgloszenie, HistoriaZmian


_local = threading.local()


def ustaw_uzytkownika(user):
    _local.user = user


def biezacy_uzytkownik():
    return getattr(_local, 'user', None)


_PRZED = {}


def _pobierz_pola(instance):
    return {f.name: getattr(instance, f.name) for f in instance._meta.fields}


@receiver(pre_save, sender=Grob)
@receiver(pre_save, sender=Osoba)
def _zapamietaj_stan(sender, instance, **kwargs):
    if instance.pk:
        try:
            _PRZED[(sender.__name__, instance.pk)] = _pobierz_pola(sender.objects.get(pk=instance.pk))
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=Grob)
@receiver(post_save, sender=Osoba)
def _zapis(sender, instance, created, **kwargs):
    przed = _PRZED.pop((sender.__name__, instance.pk), None)
    pola = {}
    if not created and przed is not None:
        po = _pobierz_pola(instance)
        for k, v in po.items():
            if przed.get(k) != v:
                pola[k] = {'przed': str(przed.get(k)), 'po': str(v)}
        if not pola:
            return
    HistoriaZmian.objects.create(
        model=sender.__name__,
        obiekt_id=instance.pk,
        obiekt_repr=str(instance)[:255],
        akcja='dodano' if created else 'zmieniono',
        pola=pola,
        user=biezacy_uzytkownik(),
    )


@receiver(post_delete, sender=Grob)
@receiver(post_delete, sender=Osoba)
def _usun(sender, instance, **kwargs):
    HistoriaZmian.objects.create(
        model=sender.__name__,
        obiekt_id=instance.pk or 0,
        obiekt_repr=str(instance)[:255],
        akcja='usunieto',
        pola={},
        user=biezacy_uzytkownik(),
    )


def _powiadom(emaile, tytul, tresc):
    emaile = [e for e in emaile if e]
    if not emaile:
        return
    try:
        send_mail(tytul, tresc, settings.DEFAULT_FROM_EMAIL, emaile, fail_silently=True)
    except Exception:
        pass


@receiver(post_save, sender=Zdjecie)
def _powiadom_zdjecie(sender, instance, created, **kwargs):
    if not created:
        return
    grob = instance.grob
    obserwujacy = grob.obserwujacy.exclude(user__email='').values_list('user__email', flat=True)
    osoby_emails = []
    for o in grob.osoby.all():
        osoby_emails += list(o.obserwujacy.exclude(user__email='').values_list('user__email', flat=True))
    emaile = list(set(list(obserwujacy) + osoby_emails))
    if emaile:
        _powiadom(emaile,
            f'Nowe zdjęcie — grób {grob}',
            f'Dodano zdjęcie do obserwowanego grobu {grob}.\n'
            f'Zobacz: ' + reverse('groby:grob_detail', args=[grob.pk]))


@receiver(post_save, sender=Wspomnienie)
def _powiadom_wspomnienie(sender, instance, created, **kwargs):
    if not created or instance.status != 'zaakceptowane':
        return
    osoba = instance.osoba
    emaile = list(osoba.obserwujacy.exclude(user__email='').values_list('user__email', flat=True))
    if emaile:
        _powiadom(emaile,
            f'Nowe wspomnienie — {osoba}',
            f'Pod profilem {osoba} pojawiło się nowe wspomnienie.\n'
            f'Zobacz: ' + reverse('groby:osoba_detail', args=[osoba.pk]))


@receiver(post_save, sender=Zgloszenie)
def _powiadom_zgloszenie(sender, instance, created, **kwargs):
    if not created:
        return
    from django.contrib.auth import get_user_model
    User = get_user_model()
    emaile = list(User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True))
    if emaile:
        cel = instance.osoba or instance.grob or '—'
        _powiadom(emaile,
            f'Nowe zgłoszenie poprawki ({cel})',
            f'Treść:\n\n{instance.tresc}\n\n'
            f'Zarządzaj: /admin/groby/zgloszenie/{instance.pk}/change/')
