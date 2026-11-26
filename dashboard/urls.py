from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("logout/", views.logout_confirm, name="logout"),
    path("members/", views.members, name="members"),
    path("members/<int:pk>/", views.member_detail, name="member"),
    path("members/<int:pk>/suspend/", views.member_toggle_suspend, name="member_suspend"),
    path("payments/", views.payments, name="payments"),
    path("payments/<str:reference>/action/", views.payment_action, name="payment_action"),
    path("events/", views.events, name="events"),
    path("events/<int:pk>/", views.event_registrations, name="event_registrations"),
]
