from django.conf.urls import url, include
from .views import *
from rest_framework import routers


router = routers.SimpleRouter()
router.register(r'sessions', SessionsViewSet)
router.register(r'peoples', PeopleViewSet)
router.register(r'places', PlaceViewSet)
router.register(r'replaces', RepViewSet)
# router.register(r'get-sessions-by-owner', SessionsownerViewSet)








urlpatterns = [
    url(r'refresh-sms-token/', refresh_sms_token_view),
    url(r'get-childern-by-token/',get_childern_view_by_token),


]


urlpatterns += router.urls