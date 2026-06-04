from django.test import TestCase
from django.urls import reverse
from attractions.models import Attraction
from attractions.filters import AttractionFilter


def make_attraction(name, category='culture', description='Test description'):
    return Attraction.objects.create(name=name, category=category, description=description)


class AttractionModelTest(TestCase):
    def test_str_returns_name(self):
        a = make_attraction('Wawel Castle')
        self.assertEqual(str(a), 'Wawel Castle')

    def test_default_ordering_is_alphabetical(self):
        make_attraction('Zebra Place')
        make_attraction('Apple Park')
        self.assertEqual(Attraction.objects.first().name, 'Apple Park')


class AttractionListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        for i in range(5):
            make_attraction(f'Culture {i}', category='culture')
        make_attraction('Family One', category='family')
        make_attraction('Couples One', category='couples')
        make_attraction('Sport One', category='sport')

    def test_full_page_returns_200(self):
        response = self.client.get(reverse('attraction-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'attractions/list.html')

    def test_full_page_has_filter_form(self):
        response = self.client.get(reverse('attraction-list'))
        self.assertContains(response, '<select')
        self.assertContains(response, 'name="category"')

    def test_htmx_category_change_uses_partial(self):
        response = self.client.get(
            reverse('attraction-list') + '?category=culture',
            HTTP_HX_REQUEST='true',
        )
        self.assertTemplateUsed(response, 'attractions/partials/filter_results.html')

    def test_htmx_category_change_returns_only_matching(self):
        response = self.client.get(
            reverse('attraction-list') + '?category=culture',
            HTTP_HX_REQUEST='true',
        )
        for attraction in response.context['attractions']:
            self.assertEqual(attraction.category, 'culture')

    def test_htmx_load_more_uses_cards_append(self):
        response = self.client.get(
            reverse('attraction-list') + '?offset=6',
            HTTP_HX_REQUEST='true',
        )
        self.assertTemplateUsed(response, 'attractions/partials/cards_append.html')

    def test_htmx_load_more_appends_correct_slice(self):
        response = self.client.get(
            reverse('attraction-list') + '?offset=6',
            HTTP_HX_REQUEST='true',
        )
        all_qs = list(Attraction.objects.all())
        expected = all_qs[6:12]
        self.assertQuerySetEqual(
            response.context['attractions'],
            expected,
            ordered=True,
        )

    def test_no_load_more_when_filtered(self):
        response = self.client.get(
            reverse('attraction-list') + '?category=family',
        )
        self.assertFalse(response.context['has_more'])

    def test_empty_state_when_no_matches(self):
        Attraction.objects.filter(category='sport').delete()
        response = self.client.get(
            reverse('attraction-list') + '?category=sport',
        )
        self.assertEqual(response.context['filter'].qs.count(), 0)
        self.assertContains(response, 'No attractions found for this category.')


class AttractionFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_attraction('Culture A', category='culture')
        make_attraction('Culture B', category='culture')
        make_attraction('Family A', category='family')

    def test_no_filter_returns_all(self):
        f = AttractionFilter({}, queryset=Attraction.objects.all())
        self.assertEqual(f.qs.count(), 3)

    def test_category_filter_returns_correct_queryset(self):
        f = AttractionFilter({'category': 'culture'}, queryset=Attraction.objects.all())
        self.assertEqual(f.qs.count(), 2)
        for a in f.qs:
            self.assertEqual(a.category, 'culture')

    def test_empty_label_allows_unfiltered(self):
        f = AttractionFilter({'category': ''}, queryset=Attraction.objects.all())
        self.assertEqual(f.qs.count(), 3)
