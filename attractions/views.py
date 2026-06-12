from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from attractions.filters import AttractionFilter
from attractions.models import Attraction, UserSavedAttraction

PAGE_SIZE = 6


def attraction_list(request):
    f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
    except (ValueError, TypeError):
        offset = 0
    qs = f.qs
    total = qs.count()
    if request.user.is_authenticated:
        saved_pks = set(UserSavedAttraction.objects.filter(user=request.user).values_list('attraction_id', flat=True))
    else:
        saved_pks = set()
    context = {
        'filter': f,
        'attractions': qs[offset:offset + PAGE_SIZE],
        'has_more': (offset + PAGE_SIZE) < total,
        'next_offset': offset + PAGE_SIZE,
        'saved_pks': saved_pks,
    }
    if request.htmx:
        template = (
            'attractions/partials/cards_append.html' if offset > 0
            else 'attractions/partials/filter_results.html'
        )
        return render(request, template, context)
    return render(request, 'attractions/list.html', context)


@login_required
def save_attraction(request, pk):
    attraction = get_object_or_404(Attraction, pk=pk)
    UserSavedAttraction.objects.get_or_create(user=request.user, attraction=attraction)
    return redirect('/')
