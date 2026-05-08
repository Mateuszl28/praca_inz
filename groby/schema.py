"""GraphQL schema (graphene-django)."""
import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import Sektor, Grob, Osoba, Tag


class SektorType(DjangoObjectType):
    liczba_grobow = graphene.Int()

    class Meta:
        model = Sektor
        fields = ('id', 'nazwa', 'opis')
        filter_fields = ['nazwa']
        interfaces = (graphene.relay.Node,)

    def resolve_liczba_grobow(self, info):
        return self.groby.count()


class GrobType(DjangoObjectType):
    typ_etykieta = graphene.String()

    class Meta:
        model = Grob
        fields = ('id', 'sektor', 'rzad', 'numer', 'typ', 'plan_x', 'plan_y', 'osoby')
        filter_fields = {'sektor': ['exact'], 'typ': ['exact'], 'numer': ['exact', 'icontains']}
        interfaces = (graphene.relay.Node,)

    def resolve_typ_etykieta(self, info):
        return self.get_typ_display()


class OsobaType(DjangoObjectType):
    wiek = graphene.Int()

    class Meta:
        model = Osoba
        fields = (
            'id', 'imie', 'drugie_imie', 'nazwisko', 'nazwisko_rodowe',
            'data_urodzenia', 'data_smierci', 'miejsce_urodzenia', 'biogram', 'grob',
        )
        filter_fields = {
            'nazwisko': ['exact', 'icontains'],
            'imie': ['exact', 'icontains'],
            'grob__sektor': ['exact'],
            'data_smierci__year': ['gte', 'lte', 'exact'],
        }
        interfaces = (graphene.relay.Node,)

    def resolve_wiek(self, info):
        return self.wiek


class TagType(DjangoObjectType):
    class Meta:
        model = Tag
        fields = ('id', 'nazwa', 'slug', 'opis', 'osoby')
        filter_fields = ['slug']
        interfaces = (graphene.relay.Node,)


class Query(graphene.ObjectType):
    sektor = graphene.relay.Node.Field(SektorType)
    sektory = DjangoFilterConnectionField(SektorType)
    grob = graphene.relay.Node.Field(GrobType)
    groby = DjangoFilterConnectionField(GrobType)
    osoba = graphene.relay.Node.Field(OsobaType)
    osoby = DjangoFilterConnectionField(OsobaType)
    tag = graphene.relay.Node.Field(TagType)
    tagi = DjangoFilterConnectionField(TagType)


schema = graphene.Schema(query=Query)
