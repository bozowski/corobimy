from django.conf import settings
from django.contrib import auth as django_auth
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            django_auth.login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
