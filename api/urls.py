from django.conf.urls import url, include
from .views import *
from rest_framework import routers


router = routers.SimpleRouter()
router.register(r'sessions', SessionsViewSet)
router.register(r'peoples', PeopleViewSet)
router.register(r'places', PlaceViewSet)
router.register(r'replaces', RepViewSet)






urlpatterns = [
    url(r'refresh-sms-token/', refresh_sms_token_view),
    # url(r'get-childern-by-rank/', get_childern_view_by_rank),
    url(r'get-childern-by-token/',get_childern_view_by_token),
    url(r'get-sessions-by-owner/', get_sessions_by_owner),
    # url(r'get-sessions-by-audience/', get_sessions_by_audience/),

]


urlpatterns += router.urls