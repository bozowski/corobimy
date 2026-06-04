from django.shortcuts import render
from attractions.filters import AttractionFilter
from attractions.models import Attraction

PAGE_SIZE = 6


def attraction_list(request):
    f = AttractionFilter(request.GET, queryset=Attraction.objects.all())
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
    except (ValueError, TypeError):
        offset = 0
    qs = f.qs
    total = qs.count()
    context = {
        'filter': f,
        'attractions': qs[offset:offset + PAGE_SIZE],
        'has_more': (offset + PAGE_SIZE) < total,
        'next_offset': offset + PAGE_SIZE,
    }
    if request.htmx:
        template = (
            'attractions/partials/cards_append.html' if offset > 0
            else 'attractions/partials/filter_results.html'
        )
        return render(request, template, context)
    return render(request, 'attractions/list.html', context)
