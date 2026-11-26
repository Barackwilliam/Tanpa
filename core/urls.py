from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("membership/", views.membership, name="membership"),
    path("news/", views.post_list, name="post_list"),
    path("news/<slug:slug>/", views.post_detail, name="post_detail"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", views.contact, name="contact"),
]
