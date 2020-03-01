import collections
import datetime
import json
import traceback
import jdatetime
from django.shortcuts import redirect, get_object_or_404, render
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from celery_sandbox.tasks import refresh_sms_token
from .serializers import *
# from api.tasks import refresh_sms_token
from django.forms.models import model_to_dict
from meeting.models import *
from django.core import serializers
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from json import JSONEncoder
from rest_framework.authtoken.models import *

logger = logging.getLogger(__name__)


class SessionsViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Sessions.objects.all().order_by('start_time')
    serializer_class = SessionsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        interposition = False
        myformat = '%Y-%m-%d %H:%M:%S'
        force = self.request.data.get('force')

        sdate = datetime.datetime.strptime(str(self.request.data.get('start_time')), myformat).date()
        stime = datetime.datetime.strptime(str(self.request.data.get('start_time')), myformat).time()

        edate = datetime.datetime.strptime(str(self.request.data.get('end_time')), myformat).date()
        etime = datetime.datetime.strptime(str(self.request.data.get('end_time')), myformat).time()

        if force == 0:
            ppls = []
            if 'audiences' in request.data:
                audiences = request.data.get('audiences')
                for audience in audiences:
                    ppls.append(audience)

            if request.data.get("selfPresent"):
                owner = Peoples.objects.get(id=request.user.id)
                ppls.append({"people": owner.mobile})

            for ppl in ppls:
                ppl_id = None
                try:
                    ppl_id = Peoples.objects.get(mobile=ppl["people"]).id
                except Peoples.DoesNotExist:
                    ppl = None
                if ppl_id is None:
                    continue

                try:
                    _sessions = Sessions.objects.filter(meeting_owner_id=ppl_id)
                except Sessions.DoesNotExist:
                    _sessions = None

                try:
                    ppl_audiences = Audiences.objects.filter(people_id=ppl_id)
                except Audiences.DoesNotExist:
                    ppl_audiences = None

                try:
                    rep_audiences = Audiences.objects.filter(rep_ppl_id=ppl_id)
                except Audiences.DoesNotExist:
                    rep_audiences = None

                for _session in _sessions:
                    if str(_session.start_time.date()) == str(sdate) or str(_session.end_time.date()) == str(edate):
                        if stime <= _session.end_time.time() <= etime or stime <= _session.start_time.time() <= etime:
                            interposition = True

                if interposition:
                    break
                for ppl_audience in ppl_audiences:
                    if str(ppl_audience.session.start_time.date()) == str(sdate) or str(
                            ppl_audience.session.end_time.date()) == str(edate):
                        if stime <= ppl_audience.session.end_time.time() <= etime or stime <= ppl_audience.session.start_time.time() <= etime:
                            interposition = True

                if interposition:
                    break
                for rep_audience in rep_audiences:
                    if str(rep_audience.session.start_time.date()) == str(sdate) or str(
                            rep_audience.session.end_time.date()) == str(edate):
                        if stime <= rep_audience.session.end_time.time() <= etime or stime <= rep_audience.session.start_time.time() <= etime:
                            interposition = True

            ppl_sesion = {"interposition": interposition}

            if interposition:
                return JsonResponse(ppl_sesion, safe=False)

        if serializer.is_valid(raise_exception=True):
            obj = serializer.save(meeting_owner=request.user)
            obj.created_time = jdatetime.datetime.now()
            obj.save()
            # obj = Sessions.objects.get(meeting_title=request.data.get('title'))
            # obj.meeting_owner = request.user
            # obj.save()
            if 'audiences' in request.data:

                # adding audiences to session
                audiences = request.data.get('audiences')
                try:
                    sessn = Sessions.objects.get(id=obj.id).id
                except Sessions.DoesNotExist:
                    sessn = None

                # see if owner is added and add him manually
                # otherwise just ignore him
                if request.data.get('selfPresent'):
                    try:
                        ppl = Peoples.objects.get(id=request.user.id)
                        Seens.objects.create(ppl_id=ppl.id, sesion_id=sessn, seen=True)
                    except Peoples.DoesNotExist:
                        ppl = None
                    Audiences.objects.create(session_id=sessn, people=ppl)
                    cred = credentials.Certificate('./civilportal.json')
                    try:
                        default_app = firebase_admin.initialize_app(cred)
                    except Exception as e:
                        print(e)
                    if ppl is not None:
                        token = ppl.fcm_token
                        if token is not None:
                            mess = "برای شما در تاریخ {} ساعت {} جلسه ای تایین شده است برای اطلاع بیشتر به اپ مراجعه نمایید".format(
                                sdate, stime)
                            message = messaging.Message(
                                data={
                                    "body": mess
                                },
                                android=messaging.AndroidConfig(priority="high"),
                                token=token,
                            )
                            try:
                                messaging.send(message)
                            except Exception as e:
                                print('Messaging Error')

                for audience in audiences:
                    try:
                        sessn = Sessions.objects.get(id=obj.id).id
                    except Sessions.DoesNotExist:
                        sessn = None
                    try:
                        ppl = Peoples.objects.get(mobile=audience.get('people'))
                        Seens.objects.create(ppl_id=ppl.id, sesion_id=sessn)
                    except Peoples.DoesNotExist:
                        ppl = None
                    Audiences.objects.create(session_id=sessn, people=ppl)

                    cred = credentials.Certificate('./civilportal.json')
                    try:
                        default_app = firebase_admin.initialize_app(cred)
                    except Exception as e:
                        print(e)
                    if ppl is not None:
                        token = ppl.fcm_token
                        if token is not None:
                            mess = "برای شما در تاریخ {} ساعت {} جلسه ای تایین شده است برای اطلاع بیشتر به اپ مراجعه نمایید".format(
                                sdate, stime)
                            message = messaging.Message(
                                data={
                                    "body": mess
                                },
                                android=messaging.AndroidConfig(priority="high"),
                                token=token,
                            )
                            try:
                                messaging.send(message)
                            except Exception as e:
                                print('Messaging Error')

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        session.delete()
        return Response(data='delete success')


class PeopleViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Peoples.objects.all()
    serializer_class = PeopleSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(meeting_owner=self.request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PeopleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PeopleSerializer(queryset, many=True)
        return Response(serializer)

    def create(self, request, *args, **kwargs):
        _id = request.user.id
        try:
            obj = Peoples.objects.get(id=_id)
        except Peoples.DoesNotExist:
            obj = Peoples.objects.create(id=_id)

        for k, v in request.data.items():
            if k == 'first_name':
                obj.first_name = v
            elif k == 'last_name':
                obj.last_name = v
            elif k == 'mobile':
                obj.mobile = v
            elif k == 'is_legal':
                obj.is_legal = v
            elif k == 'description':
                obj.description = v
            elif k == 'image':
                obj.image = v
            elif k == 'places':
                places = request.data.get('places')
            obj.save()
        for place in places:
            Places.objects.create(place_owner=obj, **place)
        leads_as_json = serializers.serialize('json', [obj, ])
        return HttpResponse(leads_as_json, content_type='json')
        # return JsonResponse([obj.first_name,obj.last_name,obj.is_legal], safe=False)
        # return JsonResponse ({'status':'ok',},encoder=JSONEncoder)


def refresh_sms_token_view(request):
    if not request.user.is_staff:
        return HttpResponse(status=403)
    else:
        try:
            # eager = refresh_sms_token.apply()
            ee = refresh_sms_token()
            # return redirect('Http://127.0.0.1:8000/admin/constance/config/')
            return redirect('Http://185.211.57.73/admin/constance/config/')
        except Exception as e:
            trace_back = traceback.format_exc()
            message = str(e) + "\n" + str(trace_back)
            logger.debug("ERROR:\n%s" % message)
            return HttpResponse(status=500)


@api_view(['GET'])
def get_self_rank(request):
    _ranks = Ranks.objects._mptt_filter(rank_owner=request.user)
    obj = Peoples.objects.get(id=request.user.id)
    response = \
        {"first_name": obj.first_name,
         "last_name": obj.last_name,
         "mobile": obj.mobile,
         "image": "http://185.211.57.73/static/uploads/%s" % obj.image,
         "rank": _ranks[0].rank_name}
    return JsonResponse(response, safe=False)


@api_view(['GET'])
def get_children(request):
    self_rank = Ranks.objects._mptt_filter(rank_owner=request.user)
    if self_rank[0].parent is not None and self_rank[0].secretary is True:
        children = Ranks.objects.get(pk=self_rank[0].parent.pk).get_descendants()
    else:
        children = Ranks.objects.get(pk=self_rank[0].pk).get_descendants()
    result = []
    for child in children:
        result.append({
            "rank_name": child.rank_name,
            "id": child.rank_owner.id,
            "first_name": child.rank_owner.first_name,
            "last_name": child.rank_owner.last_name,
            "mobile": child.rank_owner.mobile,
            "pic": "http://185.211.57.73/static/uploads/%s" % child.rank_owner.image
        })
    children = Ranks.objects.get(pk=self_rank[0].pk).extra_parents.all()
    for child in children:
        result.append({
            "rank_name": child.rank_name,
            "id": child.rank_owner.id,
            "first_name": child.rank_owner.first_name,
            "last_name": child.rank_owner.last_name,
            "mobile": child.rank_owner.mobile,
            "pic": "http://185.211.57.73/static/uploads/%s" % child.rank_owner.image
        })
    return JsonResponse(result, safe=False)


@api_view(['POST'])
def get_place_by_owner(request):
    obj = []
    try:
        places = Places.objects.filter(place_owner=request.user)
        for place in places:
            obj.append(place)
        leads_as_json = serializers.serialize('json', obj)
        return HttpResponse(leads_as_json, content_type='json')
    except Places.DoesNotExist:
        places = None
        return HttpResponse("مکانی برای شما یافت نشد.")


@api_view(['POST'])
def set_fcm_token(request):
    try:
        people = Peoples.objects.get(id=request.user.id)
        people.fcm_token = request.data.get('fcm_token')
        people.save()
        from json import JSONEncoder
        return JsonResponse({'status': 'ok', }, encoder=JSONEncoder)
    except Places.DoesNotExist:
        return HttpResponse("خطا در ثبت  توکن")


@api_view(['POST'])
def call_fcm(request):
    cred = credentials.Certificate('./civilportal.json')

    try:
        default_app = firebase_admin.initialize_app(cred)
    except Exception as e:
        print(e)
    _user = Peoples.objects.get(id=request.user.id)
    token = _user.fcm_token
    message = messaging.Message(
        data={
            "messageFrom": "Vouch!",
            "body": "برای شما در تاریخ 18 مهر جلسه ای تایین شده است برای اطلاع بیشتر به اپ مراجعه نمایید"
        },
        android=messaging.AndroidConfig(priority="high"),
        token=token,
    )
    response = messaging.send(message)
    return JsonResponse({'token': token, 'response': response}, encoder=JSONEncoder)


class RepViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Audiences.objects.all()
    serializer_class = AudienceSerializer

    def create(self, request, *args, **kwargs):
        ppl_id = request.user.id
        session_id = request.data.get('session_id')
        _rep_ppl = Peoples.objects.get(id=request.data.get('rep_ppl'))
        force = self.request.data.get('force')

        intrposition = False
        myformat = '%Y-%m-%d %H:%M:%S'
        session = Sessions.objects.get(id=session_id)
        sdate = datetime.datetime.strptime(str(session.start_time), myformat).date()
        stime = datetime.datetime.strptime(str(session.start_time), myformat).time()
        edate = datetime.datetime.strptime(str(session.end_time), myformat).date()
        etime = datetime.datetime.strptime(str(session.end_time), myformat).time()

        if force == 0:
            try:
                _audiences = Audiences.objects.filter(people_id=_rep_ppl.id)
            except Audiences.DoesNotExist:
                _audiences = None

            try:
                rep_audiences = Audiences.objects.filter(rep_ppl=_rep_ppl.id)
            except Audiences.DoesNotExist:
                rep_audiences = None

            for _audience in _audiences:
                if str(_audience.session.start_time.date()) == str(sdate) or str(
                        _audience.session.end_time.date()) == str(
                    edate):
                    if stime <= _audience.session.end_time.time() <= etime or stime <= _audience.session.start_time.time() <= etime:
                        intrposition = True
                        break

            for rep_audience in rep_audiences:
                if str(rep_audience.session.start_time.date()) == str(sdate) or str(
                        rep_audience.session.end_time.date()) == str(edate):
                    if stime <= rep_audience.session.end_time.time() <= etime or stime <= rep_audience.session.start_time.time() <= etime:
                        intrposition = True

            if intrposition:
                return JsonResponse({"interposition": intrposition}, safe=False)

        if Audiences.objects.get(people_id=ppl_id, session=session_id):
            obj = Audiences.objects.get(people=ppl_id, session=session_id)
            obj.rep_ppl = _rep_ppl
            obj.save()
            try:
                Seens.objects.get(ppl_id=_rep_ppl.id, sesion_id=session_id)
            except Seens.DoesNotExist:
                Seens.objects.create(ppl_id=_rep_ppl.id, sesion_id=session_id)

            cred = credentials.Certificate('./civilportal.json')
            # cred = credentials.Certificate('civilportal.json')
            try:
                default_app = firebase_admin.initialize_app(cred)
            except Exception as e:
                print(e)
            if obj.rep_ppl is not None:
                token = obj.rep_ppl.fcm_token
                if token is not None:
                    mess = "برای شما در تاریخ {} ساعت {} جلسه ای تایین شده است برای اطلاع بیشتر به اپ مراجعه نمایید".format(
                        sdate, stime)
                    message = messaging.Message(
                        data={
                            "body": mess
                        },
                        android=messaging.AndroidConfig(priority="high"),
                        token=token,
                    )
                    try:
                        messaging.send(message)
                    except Exception as e:
                        print('Messaging Error')
            leads_as_json = serializers.serialize('json', [obj, ])
            return HttpResponse(leads_as_json, content_type='json')


@api_view(['POST'])
def get_sessions_by_date(request):
    # sdate = jalali.Persian(request.data.get('s_time')).gregorian_datetime()
    sdate = datetime.datetime.strptime(request.data.get('time'), "%Y-%m-%d")
    s_sessions = []
    myformat = '%Y-%m-%d %H:%M:%S'
    try:
        _sessions = Sessions.objects.filter(meeting_owner=request.user)
    except Sessions.DoesNotExist:
        _sessions = None

    try:
        ppl_audiences = Audiences.objects.filter(people=request.user)
    except Audiences.DoesNotExist:
        _audiences = None

    try:
        rep_audiences = Audiences.objects.filter(rep_ppl=request.user)
    except Audiences.DoesNotExist:
        rep_audiences = None

    for _session in _sessions:
        stime = datetime.datetime.strptime(str(_session.start_time), myformat).date()
        if stime.year == sdate.year and stime.month == sdate.month and stime.day == sdate.day:
            s_sessions.append(
                {
                    'id': _session.id,
                    'meeting_title': _session.meeting_title,
                    'place_address': str(_session.address),
                    'start_time': str(_session.start_time),
                    'end_time': str(_session.end_time),
                    'created_time': str(_session.created_time),
                    'image': "http://185.211.57.73/static/uploads/%s" % str(_session.meeting_owner.image),
                    'owner': True,
                }
            )

    for _audience in ppl_audiences:
        stime = datetime.datetime.strptime(str(_audience.session.start_time), myformat).date()
        if stime.year == sdate.year and stime.month == sdate.month and stime.day == sdate.day:
            s_sessions.append(
                {
                    'id': _audience.session.id,
                    'meeting_title': _audience.session.meeting_title,
                    'place_address': str(_audience.session.address),
                    'start_time': str(_audience.session.start_time),
                    'end_time': str(_audience.session.end_time),
                    'created_time': str(_audience.session.created_time),
                    'image': "http://185.211.57.73/static/uploads/%s" % str(_audience.session.meeting_owner.image),
                    'owner': False,
                    'replace': False
                }
            )

    for _audience in rep_audiences:
        stime = datetime.datetime.strptime(str(_audience.session.start_time), myformat).date()
        if stime.year == sdate.year and stime.month == sdate.month and stime.day == sdate.day:
            s_sessions.append({
                'id': _audience.session.id,
                'meeting_title': _audience.session.meeting_title,
                'owner': False,
                'replace': True,
                'start_time': str(_audience.session.start_time),
                'end_time': str(_audience.session.end_time),
                'created_time': str(_audience.session.created_time),
                'place_address': str(_audience.session.address),
                'image': "http://185.211.57.73/static/uploads/%s" % str(_audience.session.meeting_owner.image),
            })
    return JsonResponse(s_sessions, safe=False)


@api_view(['POST'])
def get_session_by_id(request):
    r = []
    session = []
    session_id = request.data.get('id')
    try:
        _audiences = Audiences.objects.filter(session_id=session_id)
    except Audiences.DoesNotExist:
        _audiences = None
    i = 1
    for _audience in _audiences:
        rr = {}
        # rr["id"] = _audience.people.id
        rr["first_name"] = _audience.people.first_name
        rr["last_name"] = _audience.people.last_name
        rr["seen"] = Seens.objects.get(ppl_id=_audience.people.id, sesion_id=session_id).seen
        rr["image"] = "http://185.211.57.73/static/uploads/%s" % _audience.people.image
        try:
            rr["rep_first_name"] = _audience.rep_ppl.first_name
            rr["rep_last_name"] = _audience.rep_ppl.last_name
            rr["rep_seen"] = Seens.objects.get(ppl_id=_audience.rep_ppl.id, sesion_id=session_id).seen
            rr["rep_image"] = "http://185.211.57.73/static/uploads/%s" % _audience.rep_ppl.image
        except:
            rr["rep_first_name"] = None
            rr["rep_last_name"] = None
            rr["rep_seen"] = False
            rr["rep_image"] = None
        r.append(rr)
        i += 1
    try:
        _session = Sessions.objects.get(id=request.data.get('id'))
    except Sessions.DoesNotExist:
        _session = None
    session.append({
        'id': _session.id,
        'meeting_title': str(_session.meeting_title),
        'meeting_owner': str(_session.meeting_owner.first_name) + '-' + str(_session.meeting_owner.last_name),
        'owner_image': "http://185.211.57.73/static/uploads/%s" % _session.meeting_owner.image,
        'start_time': str(_session.start_time),
        'end_time': str(_session.end_time),
        'lat': _session.Latitude,
        'lng': _session.Longitude,
        'place_address': str(_session.address),
        'people': r
    })
    return JsonResponse(session, safe=False)


@api_view(['POST'])
def seen_session_by_ppl(request):
    session_id = request.data.get('session_id')
    _session = Sessions.objects.get(pk=session_id)
    _ppl = request.user
    _seen = Seens.objects.get(ppl=_ppl, sesion=_session)
    obj = []
    _seen.seen = True
    _seen.save()
    obj.append({
        'session': str(_session.meeting_title),
        'ppl': str(_ppl.first_name) + ' ' + str(_ppl.last_name),
        'seen': str(_seen.seen),
    })
    return JsonResponse(obj, safe=False)

@api_view(['GET'])
def events_shamsi(request):
    shamsi = {
        "dayOff": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        "events": [
            "آغاز نوروز",
            "عیـدنوروز/ هجـوم ماموران ستم شاهی پهلوب له مدرسه فیضیه قم (1342 هـ ش) / آغاز عملیات فتح المنین (1361 هـ ش) / روز جهانی آب",
            "عیـدنوروز / روز جهانی هوا شناسی",
            "`",
            "",
            "",
            "روز هنر های نمایشی",
            "",
            "",
            "",
            "",
            "روز جمهوری اسلامی ایران / ",
            "روز طبیعت / روز جهانی کتاب کودک",
            "",
            "روز ذخاير ژنتيکي و زيستي",
            "",
            "",
            "روز سلامتي",
            "شهادت آيت الله سيد محمد باقر صدر و خواهر ايشان بنت الهدي توسط حکومت بعث عراق(1359 هـ ق)",
            "روز ملي فناوري هسته اي / روز هنر انقلاب اسلامي(سالروز شهادت سيد مرتضي آويني 1372 هـ ش)",
            "شهادت امير سپهبد علي صياد شيرازي(1378 هـ ش) / سالروز افتتاح حساب شماره 100 به فرمان حضرت امام(رحمة الله عليه) و تأسيس بنياد مسکن انقلاب اسلامي (1358 هـ ش)",
            "",
            "روز دندانپزشکی",
            "",
            "روز بزرگداشت عطار نیشابوری",
            "",
            "",
            "",
            "روز ارتش جمهوري اسلامي و نيروي زميني",
            "",
            "",
            "روز سربازان گمنام امام زمان(عجل الله تعالي فرجه) / روز بزرگداشت سعدی ",
            "روز زمين پاک / تأسيس سپاه پاسداران انقلاب اسلامي (1358 هـ ش) / سالروز اعلام انقلاب فرهنگي (1359 هـ ش)",
            "روز بزرگداشت شيخ بهايي",
            "",
            "شکست حمله نظامي آمريکا در طبس(1359 هـ ش) ",
            "",
            "",
            "",
            "روز شوراها / روز جهانی روانشناس و مشاور",
            "روز ملي خليج فارس / آغاز عمليات بيت المقدس(1361 هـ ش) ",
            "روزجهانی کار و  کارگر",
            "شهادت استاد مرتضي مطهري (1358 هـ ش) - روز معلم",
            "",
            "",
            "روز بزرگداشت شيخ صدوق / روز جهاني ماما",
            "",
            "",
            "روز جهاني صليب سرخ و هلال احمر / روز بيماريهاي خاص و صعب العلاج",
            "روز بزرگداشت شيخ کليني / روز اسناد ملي و ميراث مکتوب",
            "روز ملی ارتباطات و روابط عمومی",
            "",
            "",
            "",
            "لغو امتياز تنباکو به فتواي آيت الله ميرزا حسن شيرازي(1270 هـ ش)",
            "روز بزرگداشت حکيم ابوالقاسم فردوسي و پاسداشت زبان فارسي",
            "",
            "روز ملي ارتباطات و روابط عمومي",
            "روز بزرگداشت حکیم عمر خیام / روز جهاني موزه و ميراث فرهنگي",
            "",
            "روز ملي جمعيت / روز ايران گردي و ايران شناسي",
            "روز اهداي عضو ، اهداي زندگي",
            "روز بهره وری و بهینه سازی مصرف / روز بزرگداشت ملاصدرا",
            "",
            "فتح خرمشهر در عمليات بيت المقدس (1361 هـ ش) و روز مقاومت، ايثار و پيروزي ",
            "روز مقاومت و پايداري - روز دزفول",
            "دومين شب قدر / روز نسيم مهر (روز حمايت از خانواده زندانيان) ",
            "",
            "افتتاح اولين دوره مجلس شوراي اسلامي (1359 هـ ش)",
            "",
            "",
            "روز جهاني بدون دخانيات",
            "",
            "",
            "",
            "خرداد رحلت حضرت امام خميني (رحمة الله عليه) رهبر کبير انقلاب و بنيانگذار جمهوري اسلامي ايران(1368 هـ ش) / خرداد انتخاب حضرت آيت الله خامنه اي به رهبري (1368 هـ ش)",
            "زنداني شدن حضرت امام خميني (رحمة الله عليه) به دست مأموران ستم شاهي پهلوي (1342 هـ ش) / قيام خونين 15 خرداد(1342 هـ ش) / روز جهاني محيط زيست",
            "",
            "",
            "",
            "",
            "روز صنايع دستي / شهادت آيت الله سعيدي به دست ماموران ستم شاهي پهلوي(1349 ه ش) ",
            "",
            "تخريب قبور ائمه بقيع عليه السلام",
            "",
            "",
            "روز گل و گياه",
            "شهادت سربازان دلير اسلام: بخارايي، اماني، صفار هرندي و نيک نژاد(1344 هـ ش)",
            "روز جهاني بيابان زدايي / روز جهاد کشاورزي(تشکيل جهاد سازندگي به فرمان حضرت امام خميني(رحمة الله عليه) 1358 ه ش)",
            "",
            "درگذشت دکتر علي شريعتي(1356 ه ش) ",
            "شهادت زائران حرم رضوي عليه السلام به دست ايادي آمريکا(عاشوراي 1373 ه ش)",
            "شهادت دکتر مصطفي چمران(1360 هـ ش) / روز بسيج استادان ",
            "روز تبليغ و اطلاع رساني ديني(سالروز صدور فرمان حضرت امام خميني (رحمة الله عليه) بر تاسيس سازمان تبليغات اسلامي-1360 هـ ش) / روز اصناف ",
            "",
            "",
            "",
            "روز جهاني مبارزه با مواد مخدر",
            "",
            "شهادت مظلومانه آيت الله دکتر بهشتي و 72 تن از ياران امام خميني(رحمة الله عليه) با انفجار بمب به دست منافقان در دفتر مرکزي حزب جمهوري اسلامي(1360 هـ ش) / روز قوه قضائيه",
            "روز مبارزه با سلاح هاي شيميايي و ميکروبي ",
            "",
            "روز صنعت و معدن / روز آزادسازي شهر مهران / روز بزرگداشت صائب تبريزي",
            "شهادت آيت الله صدوقي چهارمين شهيد محراب به دست منافقين(1361 هـ ش) / حمله دد منشانه ناوگان آمريکاي جنايتکار به هواپيماي مسافربري جمهوري اسلامي ايران توسط (1367 هـ ش) / روز بزرگداشت علامه اميني(1349 هـ ش) / روز افشاي حقوق بشر آمريکايي",
            "",
            "",
            "روز قلم / روز شهرداري و دهياري",
            "",
            "روز ماليات",
            "",
            "روز ادبيات کودکان و نوجوانان / کشف توطئه کودتاي آمريکايي در پايگاه هوايي شهيد نوژه(کودتاي نافرجام نقاب -1359 هـ ش)",
            "",
            "",
            "حمله به مسجد گوهرشاد و کشتار مردم به دست رضاخان / روز عفاف و حجاب",
            "",
            "گشايش نخستين مجلس خبرگان رهبري (1362 هـ ش) / روز گفت و گو تعامل سازنده با دنيا ",
            "",
            "روز بهزيستي و تامين اجتماعي ",
            "سالروز تأسيس نهاد شوراي نگهبان",
            "اعلام پذيرش قطعنامه 598 شوراي امنيت از سوي ايران(1367 هـ ش) / ",
            "",
            "",
            "روز بزرگداشت آيت الله سيد ابوالقاسم کاشاني",
            "",
            "",
            "",
            "",
            "",
            "سالروز عمليات افتخار آفرين مرصاد(1367 هـ ش) / ",
            "روز کارآفريني و آموزش هاي فني و حرفه اي / روز بزرگداشت ابوالفضل بيهقي ",
            "",
            "روز بزرگداشت شيخ شهاب الدين سهروردي(شيخ اشراق)",
            "روز اهداي خون",
            "روز جهاني شير مادر ",
            "شهادت آيت الله شيخ فضل الله نوري(1288 هـ ش)",
            "",
            "",
            "صدور فرمان مشروطيت(1285 هـ ش) / روز حقوق بشر اسلامي و کرامت انساني / ",
            "انفجار بمب اتمي آمريکا در هيروشيما با بيش از 160 هزار کشته و مجروح(1945 ميلادي) / سالروز شهادت امير سرلشگر خلبان عباس بابائي",
            "تشکيل جهاد دانشگاهي(1359 هـ ش) ",
            "روز خبرنگار",
            "",
            "",
            "",
            "روز حمايت از صنايع کوچک",
            "روز تشکل ها و مشارکت اجتماعي",
            "روز مقاومت اسلامي",
            "",
            "",
            "آغاز بازگشت آزادگان به ميهن اسلامي(1369 ه ش) ",
            "",
            "کودتاي آمريکا براي بازگرداندن شاه(1332 هـ ش) / گشايش مجلس خبرگان براي بررسي نهايي قانون اساسي جمهوري اسلامي ايران (1358 هـ ش)",
            "",
            "روز جهاني مسجد / روز بزرگداشت علامه مجلسي ",
            "روز صنعت دفاعي",
            "روز پزشک - روز بزرگداشت ابوعلي سينا",
            "آغاز هفته دولت / شهادت سيد علي اندرزگو(19 رمضان 1357 هـ ش) / شهادت ميثم تمار(60 هـ ق)",
            "اشغال ايران توسط متفقين و فرار رضاخان (1320 هـ ش)",
            "روز کارمند",
            "روز داروسازي - روز بزرگداشت محمدبن زکرياي رازي",
            "شهادت مظلومانه زائران خانه خدا به دست ماموران آل سعود (1366 ه ش برابر با 6 ذي الحجه 1407 هـ ق)",
            "",
            "روز مبارزه تروريسم( انفجار دفتر نخست وزيري به دست منافقان و شهادت مظلومانه شهيدان رجائي و باهنر - 1360 هـ ش)",
            "",
            "روز بانکداري اسلامي(سالروز تصويب قانون عمليات بانکي بدون ربا 1362 هـ ش) / روز تشکيل قرارگاه پدافند هوايي حضرت خاتم الانبيا ( صلى الله عليه )",
            "روزصنعت چاپ",
            "روز بهورز / روز مبارزه با استعمار انگليس(سالروز شهادت رئيسعلي دلواري) ",
            "روز تعاون / روز بزرگداشت ابوريحان بيروني / روز مردم شناسي ",
            "شهادت آيت الله قدوسي و سرتيپ وحيد دستجردي (1360 هـ ش)",
            "",
            "",
            "قيام 17 شهريور و کشتار جمعي از مردم به دست ماموران ستم شاهي پهلوي (1357 هـ ش)",
            "",
            "وفات آيت الله سيد محمود طالقاني اولين امام جمعه تهران(1358 هـ ش) ",
            "شهادت دومين شهيد محراب آيت الله مدني به دست منافقين(1360 هـ ش) ",
            "روز سینما",
            "",
            "",
            "",
            "روز خانواده و تکريم بازنشستگان",
            "",
            "روز شعر و ادب فارسي - روز بزرگداشت استاد سيد محمد حسين شهريار",
            "",
            "",
            "",
            "آغاز جنگ تحميلي (1359 هـ ش) - آغاز هفته دفاع مقدس",
            "",
            "",
            "",
            "",
            "روز جهاني جهانگردي / شکست حصر آبادان در عمليات ثامن الائمه ع (1360 هـ ش)",
            "",
            "روز بزرگداشت شمس / روز آتش نشاني و ايمني / روز بزرگداشت فرماندهان شهيد دفاع مقدس / شهادت سرداران اسلام : فلاحي، فکوري، نامجو، کلاهدوز و جهان آرا (1360 هـ ش)",
            "روز جهاني ناشنوايان / روز جهاني دريانوردي  / روز بزرگداشت مولوي ",
            "روز جهاني سالمندان / روز همبستگي و همدردي با کودکان و نوجوانان فلسطيني",
            "",
            "",
            "",
            "هجرت حضرت امام خميني (رحمة الله عليه) از عراق به پاريس (1357 هـ ش) / روز نيروي انتظامي",
            "روز دامپزشکي",
            "روز روستا و عشاير",
            "روز جهاني کودک ",
            "روز جهاني پست",
            "",
            "",
            "روز اسکان معلولان وسالمندان / روز بزرگداشت حافظ / روز ملي کاهش اثرات بلاياي طبيعي ",
            "",
            "روز جهاني استاندارد ",
            "روز جهاني نابينايان(عصاي سفيد) / شهادت پنجمين شهيد محراب آيت الله اشرفي اصفهاني به دست منافقان (1361 هـ ش)",
            "روز جهاني غذا / روز ملي پارالمپيک / روز پيوند اوليا و مربيان / سالروز واقعه به آتش کشيدن مسجد جامع شهر کرمان به دست دژخيمان رژيم پهلوي (1357 هـ ش) ",
            "",
            "روز تربيت بدني و ورزش",
            "",
            "",
            "روز صادرات",
            "",
            "شهادت مظلومانه آيت الله حاج سيد مصطفي خميني (1356 هـ ش)  / روز آمار و برنامه ريزي ",
            "",
            "",
            "اعتراض و افشاگري حضرت امام خميني (رحمة الله عليه) عليه پذيرش کاپيتولاسيون(1343 هـ ش) ",
            "",
            "",
            "",
            "شهادت محمدحسين فهميده(بسيجي 13 ساله) / روز نوجوان و بسيج دانش آموزي / روز پدافند غيرعامل",
            "",
            "شهادت آيت الله قاضي طباطبائي اولين شهيد محراب به دست منافقان(1358 هـ ش)",
            "",
            "",
            "تسخير لانه جاسوسي آمريکا به دست دانشجويان پيرو خط امام (1358 هـ ش) / روز ملي مبارزه با استکبار جهاني / روز دانش آموز / تبعيد حضرت امام خميني (ره الله عليه) از ايران به ترکيه (1343 هـ ش)",
            "روز فرهنگ عمومی",
            "",
            "",
            "",
            " روز ملی کیفیت",
            "روز جهاني علم در خدمت صلح و توسعه",
            "",
            "",
            "",
            "",
            "روز بزرگداشت آيت الله علامه سيد محمد حسين طباطبائي(1360 هـ ش)  / روز کتاب، کتابخواني و کتابدار ",
            "",
            "سالروز آزادسازي سوسنگرد",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "روز بسيج مستضعفين(تشکيل بسيج مستضعفين به فرمان حضرت امام خميني (رحمة الله عليه) -1358 هـ ش)",
            "",
            "روز نيروي دريايي",
            "",
            "روز بزرگداشت شيخ مفيد",
            "روز جهاني مبارزه با ايدز / شهادت آيت الله سيد حسن مدرس (1316 هـ ش) و روز مجلس",
            "شهادت ميرزا کوچک خان جنگلي (1300 هـ ش)",
            "روز جهاني معلولان / روز قانون اساسي جمهوري اسلامي ايران (تصويب قانون اساسي جمهوري اسلامي ايران - 1358 هـ ش) ",
            "روز بيمه",
            "",
            "روز حسابدار",
            "روز جهاني هواپيمايي /  روز دانشجو",
            "",
            "معرفي عراق به عنوان مسئول و آغازگر جنگ از سوي سازمان ملل (1370 هـ ش)",
            "تشکيل شوراي عالي انقلاب فرهنگي به فرمان حضرت امام خميني (رحمة الله عليه)(1363 هـ ش)",
            "شهادت آيت الله دستغيب سومين شهيد محراب به دست منافقان(1360 هـ ش)",
            "",
            "",
            "",
            "",
            "روز پژوهش",
            "روز حمل و نقل و رانندگان",
            "روز جهان عاري از خشونت و افراطي گري / شهادت آيت الله دکتر محمد مفتح (1358 هـ ش) / روز وحدت حوزه و دانشگاه",
            "",
            "روز تجليل از شهيدتندگويان",
            "شب يلدا",
            "",
            "",
            "روز ثبت احوال",
            "ميلاد حضرت عيسي مسيح عليه السلام",
            "روز ملي ايمني در برابر زلزله و کاهش اثرات بلاياي طبيعي",
            "",
            "شهادت آيت الله حسين غفاري به دست ماموران ستم شاهي پهلوي(1353 هـ ش) / سالروز تشکيل نهضت سوادآموزي به فرمان حضرت امام خميني (رحمة الله عليه) (1358 هـ ش)",
            "روز صنعت پتروشيمي",
            "روز بصيرت و ميثاق امت با ولايت",
            "",
            "آغاز سال جديد ميلادي",
            "",
            "ابلاغ پيام تاريخي حضرت امام خميني (رحمة الله عليه) به گورباچف رهبر شوروي سابق (1367 هـ ش)",
            "روز جهاد کشاورزي",
            "",
            "",
            "اجراي طرح استعماري حذف حجاب به دست رضاخان (1314 هـ ش) / روز بزرگداشت خواجوي کرماني",
            "",
            "قيام خونين مردم قم (1356 ه ش) ",
            " شهادت ميرزا تقي خان اميرکبير (1230 هـ ش)",
            "",
            "تشکيل شوراي انقلاب به فرمان حضرت امام خميني (رحمة الله عليه)(1357 ه ش)",
            "",
            "",
            "",
            "فرار شاه معدوم (1357 ه ش)",
            "شهادت نواب صفوي، طهماسبي، برادران واحدي و ذوالقدر از فدائيان اسلام (1334 هـ ش)",
            "",
            "روز غزه",
            "",
            "",
            "",
            "",
            "",
            "",
            "روز جهاني گمرک /  سالروز حماسه مردم آمل",
            "",
            "",
            "",
            "",
            "",
            "بازگشت حضرت امام خميني (رحمة الله عليه) به ايران (1357 هـ ش) و آغاز دهه مبارک فجر انقلاب اسلامي",
            "",
            " روز فناوري فضايي",
            "",
            "",
            "",
            "",
            " روز نیروی هوایی",
            "",
            "شکسته شدن حکومت نظامي به فرمان حضرت امام خميني (رحمة الله عليه) (1357 هـ ش)",
            "پيروزي انقلاب اسلامي و سقوط نظام شاهنشاهي(1357 هـ ش)",
            "",
            "",
            "صدور حکم تاريخي حضرت امام خميني (ره الله عليه) مبني بر ارتداد سلمان رشدي نويسنده خائن کتاب آيات شيطاني (1367 هـ ش) ",
            "",
            "",
            "",
            "قيام مردم تبريز به مناسبت چهلمين روز شهادت شهداي قم(1356 ق)",
            "",
            "",
            "",
            "کودتاي انگليسي رضاخان (1299 هـ ش)",
            "",
            "روز بزرگداشت خواجه نصيرالدين طوسي - روز مهندسي",
            "",
            "",
            "روز امور تربيتي و تربيت اسلامي / روز بزرگداشت حکيم حاج ملاهادي سبزواري",
            "روز ملي حمايت از حقوق مصرف کنندگان",
            "",
            "",
            "",
            "",
            "روز احسان و نيکوکاري",
            "روز درختکاري",
            "",
            "",
            "روز بزرگداشت سيدجمال الدين اسدآبادي / سالروز تأسيس کانونهاي فرهنگي هنري مساجد کشور",
            "",
            "روز راهيان نور ",
            "",
            "روز بزرگداشت شهدا(سالروز صدور فرمان حضرت امام خميني(رحمة الله عليه) مبني بر تاسيس بنياد شهيد انقلاب اسلامي -1358 هـ ش)",
            "",
            "",
            "بمباران شيميايي حلبچه توسط ارتش بعث عراق (1366 هـ ش) / روز بزرگداشت پروين اعتصامي ",
            "",
            "",
            "",
            "روز ملي شدن صنعت نفت ايران(1329 هـ ش) ",
            ""
        ]
    }
    return JsonResponse(shamsi, safe=False)

@api_view(['GET'])
def hijri_events(request):
    hijri = {
        "dayOff": [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0,
                   0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "events": [
            "آغاز سال جديد هجري قمري[ 1 محرم]",
            "ورود امام حسين عليه السلام به کربلا (61 ق)[ 2 محرم]",
            "",
            "",
            "",
            "",
            "",
            "",
            "تاسوعاي حسيني[ 9 محرم]",
            "عاشوراي حسيني(شهادت امام حسين عليه السلام و اصحاب آن حضرت(61 هـ ق))[ 10 محرم]",
            "روز تجليل از اسرا و مفقودان[ 11 محرم]",
            "ورود اسيران کربلا به کوفه(61 هـ ق)[ 12 محرم] / شهادت حضرت امام زين العابدين عليه السلام (95 هـ ق)[ 12 محرم]",
            "",
            "",
            "",
            "",
            "",
            "",
            "حرکت اسراي کربلا به طرف شام (61 هـ ق)[ 19 محرم]",
            "",
            "",
            "",
            "",
            "",
            "شهادت حضرت امام زين العابدين عليه السلام (95 هـ ق - به روايتي)[ 25 محرم]",
            "",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام محمدباقر عليه السلام( 57 هـ ق - به روايتي)[ 3 صفر]",
            "",
            "شهادت حضرت رقيه س دختر سه ساله امام حسين عليه السلام(61 هـ ق)[ 5 صفر]",
            "",
            "شهادت حضرت امام حسن مجتبي عليه السلام (50 هـ ق) (به روايتي)[ 7 صفر] / روز بزرگداشت سلمان فارسي[ 7 صفر]",
            "",
            "شهادت عمار بن ياسر(37 هـ ق)[ 9 صفر]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "اربعين حسيني[ 20 صفر] / ورود جابربن عبدالله انصاري به کربلا (61 هـ ق)[ 20 صفر]",
            "",
            "",
            "",
            "",
            "",
            "",
            "روز وقف[ 27 صفر]",
            " رحلت حضرت رسول اکرم صلي الله عليه و آله (11 هـ ق)[ 28 صفر] / شهادت حضرت امام حسن مجتبي عليه السلام (50 هـ ق)[ 28 صفر]",
            "",
            "شهادت حضرت امام رضا عليه السلام (203 هـ ق)[ 30 صفر]",
            "هجرت حضرت رسول اکرم صلي الله عليه و آله از مکه به مدينه[ 1 ربیع‌الاول] / شهادت حضرت امام حسن عسکري عليه السلام (به قولي)[ 1 ربیع‌الاول]",
            "",
            "",
            "خروج حضرت رسول اکرم صلي الله عليه و آله از غار(ثور) و حرکت به سوي مدينه (1 هـ ق)[ 4 ربیع‌الاول]",
            "وفات سکينه خاتون دختر امام حسين عليه السلام (117 هـ ق)[ 5 ربیع‌الاول]",
            "",
            "",
            "شهادت حضرت امام حسن عسکري عليه السلام (260 هـ ق)[ 8 ربیع‌الاول]",
            "آغاز امامت امام زمان (عجل الله تعالي فرجه)[ 9 ربیع‌الاول]",
            "وفات جناب عبدالمطلب جد پيامبر اکرم صلي الله عليه و آله[ 10 ربیع‌الاول] / ازدواج رسول اکرم صلي الله عليه و آله با حضرت خديجه کبري سلام الله عليها[ 10 ربیع‌الاول]",
            "",
            "ولادت حضرت رسول اکرم صلي الله عليه و آله به روايت اهل سنت(53 سال قبال از هجرت) - آغاز هفته وحدت[ 12 ربیع‌الاول]",
            "",
            "",
            "",
            "",
            "ميلاد حضرت رسول اکرم صلي الله عليه و آله (53 سال قبل از هجرت) و روز اخلاق و مهرورزي[ 17 ربیع‌الاول] /ولادت حضرت امام جعفر صادق عليه السلام مؤسس مذهب جعفري(83 هـ ق)[ 17 ربیع‌الاول]",
            "",
            "",
            "",
            "",
            "غزوه بني النضير[ 22 ربیع‌الاول]",
            "",
            "",
            "",
            "صلح حضرت امام حسن مجتبي عليه السلام (41 هـ ق)[ 26 ربیع‌الاول]",
            "",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت عبدالعظيم حسني عليه السلام[ 4 ربیع‌الثانی]",
            "",
            "",
            "",
            "ولادت حضرت امام حسن عسکري عليه السلام (232 هـ ق)[ 8 ربیع‌الثانی]",
            "",
            "وفات حضرت معصومه سلام الله عليها (201 هـ ق)[ 10 ربیع‌الثانی] / ميلاد حضرت امام حسن عسکري عليه السلام به قولي (232 هـ ق)[ 10 ربیع‌الثانی]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت زينب سلام الله عليها (5 هـ ق) و روز پرستار[ 5 جمادی‌الاول]",
            "",
            "",
            "",
            "",
            "جنگ جمل(36 هـ ق)[ 10 جمادی‌الاول]",
            "",
            "",
            "شهادت حضرت فاطمه زهرا سلام الله عليها (به روايت 75 روز - 11 هـ ق)[ 13 جمادی‌الاول]",
            "",
            "ولادت حضرت سجاد عليه السلام به قولي(38 هـ ق)[ 15 جمادی‌الاول]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            " شهادت حضرت فاطمه زهرا سلام الله عليها (به روايت 95 روز - 11 هـ ق)[ 3 جمادی‌الثانی]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "سالروز وفات حضرت ام البنين سلام الله عليها[ 13 جمادی‌الثانی] / روز تکريم مادران و همسران شهدا[ 13 جمادی‌الثانی]",
            "",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت فاطمه زهرا سلام الله عليها (هشتم قبل از هجرت) و روز زن[ 20 جمادی‌الثانی] / تولد حضرت امام خميني(رحمة الله عليه) رهبر کبير انقلاب اسلامي(1320 هـ ق)[ 20 جمادی‌الثانی]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام محمد باقر عليه السلام (57 هـ ق)[ 1 رجب]",
            "",
            "شهادت حضرت امام علي النقي الهادي عليه السلام (254 هـ ق)[ 3 رجب]",
            "",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام محمد تقي عليه السلام <<جواد الائمه>> (195 هـ ق)[ 10 رجب]",
            "",
            "",
            "ولادت حضرت امام علي عليه السلام (23 سال قبل از هجرت)[ 13 رجب] / آغاز ايام البيض (اعتکاف)[ 13 رجب]",
            "",
            "وفات حضرت زينب سلام الله عليها (62 هـ ق)[ 15 رجب] / تغيير قبله از بيت المقدس به کعبه(2 هـ ق)[ 15 رجب]",
            "",
            "",
            "وفات ابراهيم فرزند پيامبر اکرم صلي الله عليه و آله (10 هـ ق)[ 18 رجب]",
            "",
            "",
            "",
            "",
            "",
            "فتح خيبر توسط حضرت اميرالمومنين علي عليه السلام (7 هـ ق)[ 24 رجب]",
            "شهادت حضرت امام موسي کاظم عليه السلام (183 هـ ق)[ 25 رجب]",
            "وفات حضرت ابوطالب عموي پيامبر اکرم (صلي الله عليه و آله) و پدر اميرالمومنين عليه السلام (3 سال قبل از هجرت)[ 26 رجب]",
            "مبعث حضرت رسول اکرم (صلي الله عليه و آله) (13 سال قبل از هجرت)[ 27 رجب]",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام حسين عليه السلام ( 4 هـ ق) و روز پاسدار[ 3 شعبان]",
            "ولادت حضرت ابوالفضل العباس عليه السلام ( 26 هـ ق) و روز جانباز[ 4 شعبان]",
            "ولادت حضرت امام زين العابدين عليه السلام ( 38 هـ ق)[ 5 شعبان]",
            "",
            "",
            "",
            "",
            "",
            "ولادت حضرت علي اکبر عليه السلام (33 هـ ق) و روز جوان[ 11 شعبان]",
            "",
            "",
            "",
            "ولادت حضرت قائم عجل الله تعالي فرجه(255 هـ ق)[ 15 شعبان] / روز جهاني مستضعفين[ 15 شعبان]",
            "",
            "",
            "",
            "غزوه بني المصطلق(6 هـ ق)[ 19 شعبان]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "وفات حضرت خديجه کبري سلام الله عليها (3 سال قبل از هجرت)[ 10 رمضان]",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام حسن مجتبي عليه السلام (3هـ ق) و روز اکرام[ 15 رمضان]",
            "",
            "معراج رسول اکرم (صلي الله عليه و آله) (6 ماه قبل از هجرت)[ 17 رمضان] / جنگ بدر(2 هـ ق)[ 17 رمضان]",
            "اولين شب قدر[ 18 رمضان]",
            "ضربت خوردن حضرت علي عليه السلام (40 ق)[ 19 رمضان]",
            "فتح مکه(8 هـ ق)[ 20 رمضان] / دومين شب قدر[ 20 رمضان]",
            "شهادت حضرت اميرالمومنين علي عليه السلام (40 هـ ق)[ 21 رمضان]",
            "سومين شب قدر[ 22 رمضان]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            " عيد سعيد فطر[ 1 شوال]",
            "تعطيل به مناسبت عيد سعيد فطر[ 2 شوال]",
            "",
            "",
            "ورود جناب مسلم ابن عقيل به کوفه(60 هـ ق)[ 5 شوال]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "شهادت حضرت حمزه (3 هـ ق)[ 15 شوال] / وفات حضرت عبدالعظيم حسني (252 هـ ق)[ 15 شوال]",
            "",
            "غزوه خندق (5 هـ ق)[ 17 شوال] / روز فرهنگ پهلواني و ورزش زورخانه اي[ 17 شوال]",
            "",
            "",
            "",
            "فتح اندلس به دست مسلمانان (92 هـ ق)[ 21 شوال]",
            "",
            "",
            "",
            "شهادت حضرت امام جعفر صادق عليه السلام (148 هـ ق)[ 25 شوال]",
            "",
            "",
            "",
            "",
            "ولادت حضرت معصومه سلام الله عليها (173 هـ ق) و روز دختران[ 1 ذی القعده]",
            "",
            "",
            "",
            "روز تجليل از امامزادگان و بقاع متبرکه[ 5 ذی القعده] / روز بزرگداشت حضرت صالح بن موسي کاظم عليه السلام[ 5 ذی القعده]",
            "روز بزرگداشت حضرت احمدبن موسي شاهچراغ عليه السلام[ 6 ذی القعده]",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام رضا عليه السلام (148 هـ ق)[ 11 ذی القعده]",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "شهادت حضرت امام رضا عليه السلام به روايتي (202 هـ ق)[ 23 ذی القعده] / غزوه بني قريظه[ 23 ذی القعده]",
            "",
            "روز دحوالارض-حرکت امام رضا از مدينه به سمت خراسان(200 هـ ق)[ 25 ذی القعده]",
            "",
            "",
            "",
            "شهادت حضرت امام محمد تقي عليه السلام (220 هـ ق)[ 30 ذی القعده]",
            "شهادت حضرت امام محمد تقي عليه السلام (220 هـ ق)[ 30 ذی القعده]",
            "روز ازدواج[ 1 ذی الحجه] / ازدواج حضرت اميرالمونين علي (عليه السلام ) و حضرت زهرا سلام الله عليها (2هـ ق)[ 1 ذی الحجه]",
            "",
            "ورود پيامبر اکرم (صلي الله عليه و آله)به مکه در سفر حجه الوداع(10 هـ ق)[ 3 ذی الحجه]",
            "",
            "",
            "",
            "شهادت امام محمد باقر عليه السلام (114 هـ ق)[ 7 ذی الحجه]",
            "حرکت امام حسين عليه السلام از مکه بسوي کربلا (60 هـ ق)[ 8 ذی الحجه]",
            "روز عرفه[ 9 ذی الحجه] / شهادت مسلم بن عقيل و هاني ابن عروه(60 هـ ق)[ 9 ذی الحجه]",
            "عيد سعيد قربان[ 10 ذی الحجه]",
            "",
            "",
            "",
            "",
            "ولادت حضرت امام علي النقي الهادي عليه السلام (212 هـ ق)[ 15 ذی الحجه]",
            "",
            "",
            "عيد سعيد غدير (10هـ ق)[ 18 ذی الحجه]",
            "",
            "ولادت حضرت امام موسي کاظم عليه السلام (128 هـ ق)[ 20 ذی الحجه]",
            "",
            "",
            "",
            "روز مباهله پيامبر اسلام صلي الله عليه و آله (10 ه ق)[ 24 ذی الحجه]",
            "",
            "",
            "",
            "",
            ""
        ]
    }
    return JsonResponse(hijri, safe=False)
