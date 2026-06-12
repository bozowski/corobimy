import django_filters

from attractions.models import CATEGORY_CHOICES, Attraction


class AttractionFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(
        choices=CATEGORY_CHOICES,
        empty_label='All categories',
    )

    class Meta:
        model = Attraction
        fields = ['category']
