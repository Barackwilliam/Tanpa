from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("badge/<uuid:token>/", views.verify, name="verify"),
    path("badge/<uuid:token>/check-in/", views.check_in, name="check_in"),
    path("<slug:slug>/", views.event_detail, name="detail"),
    path("<slug:slug>/register/", views.register, name="register"),
    path("<slug:slug>/pay/", views.pay, name="pay"),
    path("<slug:slug>/badge.pdf", views.badge, name="badge"),
]
