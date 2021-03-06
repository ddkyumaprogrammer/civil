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
    url(r'events_shamsi/',events_shamsi),
    url(r'events_hijri/',hijri_events),
    url(r'get-children/',get_children),
    url(r'get_self_rank/',get_self_rank),
    url(r'get-sessions-by-date/',get_sessions_by_date),
    url(r'session-by-id/', get_session_by_id),
    url(r'place-by-owner/', get_place_by_owner),
    url(r'seen-session-by-ppl/', seen_session_by_ppl),
    url(r'set_fcm_token/', set_fcm_token),
    url(r'call_fcm/', call_fcm),
]

urlpatterns += router.urls