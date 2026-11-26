from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("<str:reference>/", views.checkout, name="checkout"),
    path("<str:reference>/mobile/", views.pay_mobile, name="mobile"),
    path("<str:reference>/manual/", views.pay_manual, name="manual"),
    path("<str:reference>/test/", views.pay_sandbox, name="sandbox"),
    path("<str:reference>/cancel/", views.cancel, name="cancel"),
    path("<str:reference>/waiting/", views.waiting, name="waiting"),
    path("<str:reference>/status.json", views.status_json, name="status"),
    path("<str:reference>/receipt/", views.receipt, name="receipt"),
]

callback_urlpatterns = [
    path("azampay/<str:token>/", views.azampay_callback, name="azampay_callback"),
]
