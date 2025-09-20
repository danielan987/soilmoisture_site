from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from .forms import CounterForm

def index(request: HttpRequest) -> HttpResponse:
    form = CounterForm(initial={"value": 0})
    return render(request, "core/index.html", {"form": form})

def increment_counter(request: HttpRequest) -> HttpResponse:
    """
    HTMX endpoint: expects POST with 'value', returns the updated partial.
    """
    if request.method == "POST":
        try:
            current = int(request.POST.get("value", "0"))
        except ValueError:
            current = 0
        new_value = current + 1
        return render(request, "core/_counter_partial.html", {"value": new_value})
    # Fallback for non-POST access
    return render(request, "core/_counter_partial.html", {"value": 0})

