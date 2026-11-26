from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from events.models import Event
from members.models import Member
from payments.models import FeeSchedule

from .forms import ContactForm
from .models import GalleryImage, Leader, Partner, Post


def home(request):
    today = timezone.localdate()
    return render(request, "core/home.html", {
        "next_event": Event.objects.filter(is_published=True, end_date__gte=today).order_by("start_date").first(),
        "posts": Post.objects.filter(is_published=True, published_at__lte=timezone.now())[:3],
        "gallery": GalleryImage.objects.filter(is_featured=True)[:5] or GalleryImage.objects.all()[:5],
        "leaders": Leader.objects.filter(is_active=True)[:4],
        "partners": Partner.objects.all(),
        "member_count": Member.objects.filter(entry_fee_paid=True).count(),
        "active_count": Member.objects.active().count(),
        "event_count": Event.objects.filter(is_published=True).count(),
        "region_count": Member.objects.filter(entry_fee_paid=True).values("region").distinct().count(),
        "fees": FeeSchedule.for_year(),
    })


def about(request):
    return render(request, "core/about.html", {"leaders": Leader.objects.filter(is_active=True)})


def membership(request):
    return render(request, "core/membership.html", {"fees": FeeSchedule.for_year()})


def post_list(request):
    qs = Post.objects.filter(is_published=True, published_at__lte=timezone.now())
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "core/post_list.html", {"page": page})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    more = Post.objects.filter(is_published=True).exclude(pk=post.pk)[:3]
    return render(request, "core/post_detail.html", {"post": post, "more": more})


def gallery(request):
    images = GalleryImage.objects.all()
    albums = sorted({i.album for i in images if i.album})
    album = request.GET.get("album")
    if album:
        images = images.filter(album=album)
    return render(request, "core/gallery.html", {"images": images, "albums": albums, "album": album})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data.get("website"):  # honeypot
            return redirect("core:contact")
        form.save()
        messages.success(request, "Thank you for contacting TANPA. We will get back to you soon.")
        return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form})
