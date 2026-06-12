from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from attractions.models import Attraction, UserSavedAttraction
from attractions.filters import AttractionFilter

User = get_user_model()


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


class SaveAuthGateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.attraction = make_attraction('Gate Test Attraction')
        cls.user = User.objects.create_user('gateuser', password='testpass123!')

    def test_anonymous_post_is_rejected(self):
        url = reverse('attraction-save', args=[self.attraction.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])
        self.assertEqual(UserSavedAttraction.objects.count(), 0)

    def test_authenticated_post_saves_and_redirects(self):
        self.client.force_login(self.user)
        url = reverse('attraction-save', args=[self.attraction.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('attraction-list'))
        self.assertTrue(
            UserSavedAttraction.objects.filter(user=self.user, attraction=self.attraction).exists()
        )

    def test_invalid_pk_returns_404(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('attraction-save', args=[99999]))
        self.assertEqual(response.status_code, 404)


class UserSaveIsolationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.attraction = make_attraction('Isolation Test Attraction')
        cls.user_a = User.objects.create_user('isolation_user_a', password='testpass123!')
        cls.user_b = User.objects.create_user('isolation_user_b', password='testpass123!')
        UserSavedAttraction.objects.create(user=cls.user_a, attraction=cls.attraction)

    def test_user_b_context_excludes_user_a_saves(self):
        self.client.force_login(self.user_b)
        response = self.client.get(reverse('attraction-list'))
        self.assertNotIn(self.attraction.pk, response.context['saved_pks'])


class SaveAcrossAuthTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.attraction = make_attraction('Auth Test Attraction')
        cls.user = User.objects.create_user('authuser', password='testpass123!')

    def test_login_path_save_persists(self):
        save_url = reverse('attraction-save', args=[self.attraction.pk])
        self.client.post(save_url)
        self.client.post(
            reverse('login'),
            {'username': 'authuser', 'password': 'testpass123!', 'next': save_url},
            follow=True,
        )
        self.assertTrue(
            UserSavedAttraction.objects.filter(user=self.user, attraction=self.attraction).exists()
        )

    def test_register_path_save_persists(self):
        save_url = reverse('attraction-save', args=[self.attraction.pk])
        self.client.post(save_url)
        self.client.post(
            reverse('register'),
            {
                'username': 'newreguser',
                'password1': 'testpass123!',
                'password2': 'testpass123!',
                'next': save_url,
            },
            follow=True,
        )
        new_user = User.objects.get(username='newreguser')
        self.assertTrue(
            UserSavedAttraction.objects.filter(user=new_user, attraction=self.attraction).exists()
        )
