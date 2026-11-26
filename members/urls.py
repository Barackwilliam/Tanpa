from django.urls import path

from . import views

app_name = "members"

urlpatterns = [
    path("join/", views.register, name="register"),
    path("portal/", views.dashboard, name="dashboard"),
    path("portal/profile/", views.profile, name="profile"),
    path("portal/payments/", views.payments, name="payments"),
    path("portal/pay/<str:purpose>/", views.start_payment, name="pay"),
    path("portal/id-card.pdf", views.id_card, name="id_card"),
    path("verify/", views.verify_lookup, name="verify_lookup"),
    path("verify/<uuid:token>/", views.verify, name="verify"),
]
