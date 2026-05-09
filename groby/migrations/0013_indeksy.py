"""Dodaje brakujące indeksy do najczęstszych zapytań."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('groby', '0012_zdjeciewpisu'),
    ]
    operations = [
        migrations.AddIndex(
            model_name='osoba',
            index=models.Index(fields=['nazwisko', 'imie'], name='osoba_nazw_imie_idx'),
        ),
        migrations.AddIndex(
            model_name='osoba',
            index=models.Index(fields=['data_smierci'], name='osoba_data_smierci_idx'),
        ),
        migrations.AddIndex(
            model_name='grob',
            index=models.Index(fields=['plan_x', 'plan_y'], name='grob_pozycja_idx'),
        ),
    ]
