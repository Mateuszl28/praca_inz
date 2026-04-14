from django import template

register = template.Library()


@register.filter(name='odmien')
def polish_plural(value, forms):
    """
    Zwraca właściwą polską formę rzeczownika zależną od liczby.
    Użycie w szablonie:  {{ n|odmien:"grób,groby,grobów" }}

    Reguły języka polskiego:
      - 1               -> forma pojedyncza            (singular)
      - 2-4, 22-24, ... -> forma mnoga "kilka"         (few)
      - pozostałe       -> forma mnoga dopełniaczowa   (many)
    """
    try:
        n = abs(int(value))
    except (TypeError, ValueError):
        return ''
    parts = [p.strip() for p in forms.split(',')]
    if len(parts) != 3:
        return ''
    singular, few, many = parts
    if n == 1:
        return singular
    if 2 <= n % 10 <= 4 and not (10 <= n % 100 <= 20):
        return few
    return many
