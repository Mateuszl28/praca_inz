"""Po dodaniu pola Osoba.epitafium w 0019 SQLite przebudowal tabele groby_osoba,
co skasowalo triggery FTS5. Tu odtwarzamy je oraz repopulujemy indeks osoba_fts.
"""
from django.db import migrations


SQL_REBUILD = """
DROP TRIGGER IF EXISTS osoba_au;
DROP TRIGGER IF EXISTS osoba_ad;
DROP TRIGGER IF EXISTS osoba_ai;

INSERT INTO osoba_fts(osoba_fts) VALUES ('delete-all');
INSERT INTO osoba_fts(rowid, imie, drugie_imie, nazwisko, nazwisko_rodowe, miejsce_urodzenia, biogram)
SELECT id, COALESCE(imie,''), COALESCE(drugie_imie,''), COALESCE(nazwisko,''),
       COALESCE(nazwisko_rodowe,''), COALESCE(miejsce_urodzenia,''), COALESCE(biogram,'')
FROM groby_osoba;

CREATE TRIGGER IF NOT EXISTS osoba_ai AFTER INSERT ON groby_osoba BEGIN
    INSERT INTO osoba_fts(rowid, imie, drugie_imie, nazwisko, nazwisko_rodowe, miejsce_urodzenia, biogram)
    VALUES (new.id, COALESCE(new.imie,''), COALESCE(new.drugie_imie,''), COALESCE(new.nazwisko,''),
            COALESCE(new.nazwisko_rodowe,''), COALESCE(new.miejsce_urodzenia,''), COALESCE(new.biogram,''));
END;

CREATE TRIGGER IF NOT EXISTS osoba_ad AFTER DELETE ON groby_osoba BEGIN
    INSERT INTO osoba_fts(osoba_fts, rowid, imie, drugie_imie, nazwisko, nazwisko_rodowe, miejsce_urodzenia, biogram)
    VALUES ('delete', old.id, COALESCE(old.imie,''), COALESCE(old.drugie_imie,''), COALESCE(old.nazwisko,''),
            COALESCE(old.nazwisko_rodowe,''), COALESCE(old.miejsce_urodzenia,''), COALESCE(old.biogram,''));
END;

CREATE TRIGGER IF NOT EXISTS osoba_au AFTER UPDATE ON groby_osoba BEGIN
    INSERT INTO osoba_fts(osoba_fts, rowid, imie, drugie_imie, nazwisko, nazwisko_rodowe, miejsce_urodzenia, biogram)
    VALUES ('delete', old.id, COALESCE(old.imie,''), COALESCE(old.drugie_imie,''), COALESCE(old.nazwisko,''),
            COALESCE(old.nazwisko_rodowe,''), COALESCE(old.miejsce_urodzenia,''), COALESCE(old.biogram,''));
    INSERT INTO osoba_fts(rowid, imie, drugie_imie, nazwisko, nazwisko_rodowe, miejsce_urodzenia, biogram)
    VALUES (new.id, COALESCE(new.imie,''), COALESCE(new.drugie_imie,''), COALESCE(new.nazwisko,''),
            COALESCE(new.nazwisko_rodowe,''), COALESCE(new.miejsce_urodzenia,''), COALESCE(new.biogram,''));
END;
"""

SQL_REVERSE = """
DROP TRIGGER IF EXISTS osoba_au;
DROP TRIGGER IF EXISTS osoba_ad;
DROP TRIGGER IF EXISTS osoba_ai;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('groby', '0019_batch93_sondy_kondolencje_zbiorki_notki_epitafium'),
    ]
    operations = [
        migrations.RunSQL(sql=SQL_REBUILD, reverse_sql=SQL_REVERSE),
    ]
