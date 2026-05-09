"""Sygnały Django -> wpisy do HistoriaZmian dla Grob i Osoba.

Bieżący użytkownik jest pobierany z thread-local (ustawianego przez middleware).
"""
import threading
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from .models import (
    Grob, Osoba, Zdjecie, Wspomnienie, Zgloszenie, HistoriaZmian, Swieca, Relacja,
    Trasa, Wpis, Odznaka, UzytkownikOdznaka, Webhook,
    Komentarz, PostForum, OpiekunGrobu, Powiadomienie,
)


def wyslij_webhook(event, payload):
    """Wysyła event do wszystkich aktywnych Webhook-ów (generic / Discord / Slack)."""
    import json
    import urllib.request
    for w in Webhook.objects.filter(event=event, aktywny=True):
        try:
            if w.typ == 'discord':
                body = json.dumps({'content': f'**{event}**: {payload.get("tytul", str(payload))}'}).encode()
            elif w.typ == 'slack':
                body = json.dumps({'text': f'*{event}*: {payload.get("tytul", str(payload))}'}).encode()
            else:
                body = json.dumps({'event': event, 'payload': payload}).encode()
            req = urllib.request.Request(w.url, data=body, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=3).read()
            Webhook.objects.filter(pk=w.pk).update(licznik_wywolan=w.licznik_wywolan + 1)
        except Exception:
            pass


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


def _przyznaj_odznake(user, kod):
    if not user or not user.is_authenticated:
        return
    odznaka = Odznaka.objects.filter(kod=kod).first()
    if odznaka:
        UzytkownikOdznaka.objects.get_or_create(user=user, odznaka=odznaka)


@receiver(post_save, sender=Swieca)
def _odznaka_strazn(sender, instance, created, **kwargs):
    if created and instance.autor_user_id:
        if Swieca.objects.filter(autor_user=instance.autor_user).count() >= 10:
            _przyznaj_odznake(instance.autor_user, 'strazn')


@receiver(post_save, sender=Wspomnienie)
def _odznaka_kron(sender, instance, **kwargs):
    if instance.status == 'zaakceptowane' and instance.autor_user_id:
        if Wspomnienie.objects.filter(autor_user=instance.autor_user, status='zaakceptowane').count() >= 5:
            _przyznaj_odznake(instance.autor_user, 'kron')


@receiver(post_save, sender=Trasa)
def _odznaka_prze(sender, instance, **kwargs):
    if instance.opublikowana and instance.autor_id:
        _przyznaj_odznake(instance.autor, 'prze')


@receiver(post_save, sender=Wpis)
def _odznaka_hist(sender, instance, **kwargs):
    if instance.opublikowany and instance.autor_id:
        _przyznaj_odznake(instance.autor, 'hist')


@receiver(post_save, sender=Zgloszenie)
def _powiadom_zgloszenie(sender, instance, created, **kwargs):
    if not created:
        return
    from django.contrib.auth import get_user_model
    User = get_user_model()
    emaile = list(User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True))
    cel = instance.osoba or instance.grob or '—'
    if emaile:
        _powiadom(emaile,
            f'Nowe zgłoszenie poprawki ({cel})',
            f'Treść:\n\n{instance.tresc}\n\n'
            f'Zarządzaj: /admin/groby/zgloszenie/{instance.pk}/change/')
    wyslij_webhook('zgloszenie.nowe', {'tytul': f'Zgłoszenie #{instance.pk} ({cel})', 'tresc': instance.tresc[:200]})


# ----- Batch 91: in-app notifications -----


def _powiadom_inapp(user, typ, tresc, url=''):
    """Tworzy wpis Powiadomienie dla użytkownika (cicho ignoruje brak usera)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return
    Powiadomienie.objects.create(user=user, typ=typ, tresc=tresc[:300], url=url[:300])


@receiver(post_save, sender=Komentarz)
def _powiadom_komentarz(sender, instance, created, **kwargs):
    """Powiadom autora wspomnienia o nowym komentarzu (jeśli to nie on sam komentuje)."""
    if not created:
        return
    autor_wspomnienia = getattr(instance.wspomnienie, 'autor_user', None)
    komentujacy = getattr(instance, 'autor_user', None) or getattr(instance, 'user', None)
    if autor_wspomnienia and autor_wspomnienia != komentujacy:
        try:
            url = reverse('groby:osoba_detail', args=[instance.wspomnienie.osoba_id])
        except Exception:
            url = ''
        _powiadom_inapp(autor_wspomnienia, 'komentarz',
                        f'Nowy komentarz pod Twoim wspomnieniem o {instance.wspomnienie.osoba}', url)


@receiver(post_save, sender=PostForum)
def _powiadom_forum(sender, instance, created, **kwargs):
    """Powiadom autora wątku o nowej odpowiedzi (jeśli to nie on sam odpowiada)."""
    if not created:
        return
    watek = instance.watek
    autor_watku = getattr(watek, 'autor_user', None) or getattr(watek, 'autor', None)
    autor_post = getattr(instance, 'autor_user', None) or getattr(instance, 'autor', None)
    if autor_watku and autor_watku != autor_post:
        _powiadom_inapp(autor_watku, 'forum',
                        f'Nowa odpowiedź w wątku „{watek.tytul}”',
                        f'/grob/{watek.grob_id}/forum/' if getattr(watek, 'grob_id', None) else '')


@receiver(post_save, sender=OpiekunGrobu)
def _powiadom_opiekun(sender, instance, created, **kwargs):
    if created:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for staff in User.objects.filter(is_staff=True):
            _powiadom_inapp(staff, 'opieka',
                            f'Nowe zgłoszenie opieki nad grobem {instance.grob} ({instance.user})',
                            f'/admin/groby/opiekungrobu/{instance.pk}/change/')
    else:
        if instance.status in ('aktywny', 'odrzucony'):
            _powiadom_inapp(instance.user, 'opieka',
                            f'Twoje zgłoszenie opieki nad {instance.grob}: {instance.get_status_display()}',
                            f'/grob/{instance.grob_id}/')
