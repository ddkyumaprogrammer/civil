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
                if str(_audience.session.start_time.date()) == str(sdate) or str(_audience.session.end_time.date()) == str(
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
