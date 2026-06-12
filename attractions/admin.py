from django.contrib import admin
from attractions.models import Attraction, UserSavedAttraction


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)


admin.site.register(UserSavedAttraction)
