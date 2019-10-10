from django.conf.urls import url, include
from .views import *
from rest_framework import routers

router = routers.SimpleRouter()
router.register(r'sessions', SessionsViewSet)
router.register(r'peoples', PeopleViewSet)
# router.register(r'places', PlaceViewSet)
router.register(r'replaces', RepViewSet)
# router.register(r'session-by-id', SessionidViewSet)

urlpatterns = [
    url(r'get-childern-by-token/',get_childern_view_by_token),
    url(r'get-sessions-by-date/',get_sessions_by_date),
    url(r'session-by-id/', get_session_by_id),
    url(r'place-by-owner/', get_place_by_owner),
    url(r'seen-session-by-ppl/', seen_session_by_ppl),
    url(r'set_fcm_token/', set_fcm_token),
    url(r'call_fcm/', call_fcm),
]

urlpatterns += router.urls