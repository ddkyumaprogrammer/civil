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
        force = self.request.data.get('force')
        intrposition = []
        myformat = '%Y-%m-%d %H:%M:%S'
        sdate = datetime.datetime.strptime(str(self.request.data.get('start_time')), myformat).date()
        edate = datetime.datetime.strptime(str(self.request.data.get('end_time')), myformat).date()
        stime = datetime.datetime.strptime(str(self.request.data.get('start_time')), myformat).time()
        etime = datetime.datetime.strptime(str(self.request.data.get('end_time')), myformat).time()
        force = self.request.data.get('force')

        ppls = []
        ppls.append(request.user.mobile)
        if 'audiences' in request.data:
            audiences = request.data.get('audiences')[0].values()
            for audience in audiences:
                for i in audience:
                    ppls.append(i)
        ppl_ower_name = []
        ppl_ower_id = []
        ppl_aud_name = []
        ppl_aud_id = []
        ppl_rep_name = []
        ppl_rep_id = []
        for ppl in ppls:
            try:
                ppl_id = Peoples.objects.get(mobile=ppl).id
            except Peoples.DoesNotExist:
                ppl = None

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
                s = {}
                if str(_session.start_time.date()) == str(sdate) or str(_session.end_time.date()) == str(edate):
                    if stime <= _session.end_time.time() <= etime or stime <= _session.start_time.time() <= etime:
                        s[str(_session.meeting_owner.first_name) + ' ' + str(_session.meeting_owner.last_name)] = str(
                            _session.id)
                        intrposition.append(s)
                        ppl_ower_name.append(_session.meeting_owner.id)
                        ppl_ower_id.append(_session.id)
            for ppl_audience in ppl_audiences:
                k = {}
                if str(ppl_audience.session.start_time.date()) == str(sdate) or str(
                        ppl_audience.session.end_time.date()) == str(
                    edate):
                    if stime <= ppl_audience.session.end_time.time() <= etime or stime <= ppl_audience.session.start_time.time() <= etime:
                        k[str(ppl_audience.people.first_name) + " " + str(ppl_audience.people.last_name)] = str(
                            ppl_audience.session.id)
                        intrposition.append(k)
                        ppl_aud_name.append(ppl_audience.people.id)
                        ppl_aud_id.append(ppl_audience.session.id)
            for rep_audience in rep_audiences:
                k = {}
                if str(rep_audience.session.start_time.date()) == str(sdate) or str(
                        rep_audience.session.end_time.date()) == str(
                    edate):
                    if stime <= rep_audience.session.end_time.time() <= etime or stime <= rep_audience.session.start_time.time() <= etime:
                        k[str(rep_audience.people.first_name) + " " + str(rep_audience.people.last_name)] = str(
                            rep_audience.session.id)
                        intrposition.append(k)
                        ppl_rep_name.append(rep_audience.rep_ppl.id)
                        ppl_rep_id.append(rep_audience.session.id)

        owner = len(ppl_ower_name)
        aud = len(ppl_aud_name)
        rep = len(ppl_rep_name)
        ppl_ower = []
        ppl_aud = []
        ppl_rep = []
        for i in range(owner):
            w = {}
            w[ppl_ower_name[i]] = ppl_ower_id[i]
            ppl_ower.append(w)
        for i in range(aud):
            w = {}
            w[ppl_aud_name[i]] = ppl_aud_id[i]
            ppl_aud.append(w)
        for i in range(rep):
            w = {}
            w[ppl_rep_name[i]] = ppl_rep_id[i]
            ppl_rep.append(w)
        no_dupes_owner = [x for n, x in enumerate(ppl_ower) if x not in ppl_ower[:n]]
        no_dupes_aud = [x for n, x in enumerate(ppl_aud) if x not in ppl_aud[:n]]
        no_dupes_rep = [x for n, x in enumerate(ppl_rep) if x not in ppl_rep[:n]]
        ppl_sesion = {}
        ppl_sesion["تشکیل دهنده"] = no_dupes_owner
        ppl_sesion["دعوت شده"] = no_dupes_aud
        ppl_sesion["جایگزین"] = no_dupes_rep

        # ppl_sesionp = {}
        # ppl_sesionp["تشکیل دهنده"] = ppl_ower
        # ppl_sesionp["دعوت شده"] = ppl_aud
        # ppl_sesionp["جایگزین"] = ppl_rep
        # print(ppl_sesionp)

        if intrposition != [] and force == 0:
            return JsonResponse(ppl_sesion, safe=False)
            # return Response( ','.join(map(str, intrposition))+"--"+"تداخل با جلسه")


        else:
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

                        cred = credentials.Certificate('/opt/w/civil/civilportal.json')
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
        newdict = {'item': "test"}
        newdict.update(serializer.data)
        newdict['item'] = 'data'
        return Response(newdict)

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


@api_view(['POST'])
def get_childern_view_by_token(request):
    try:
        ranks = Ranks.objects.all()
    except Ranks.DoesNotExist:
        return HttpResponse('جایگاهی تعریف نشده است.', status=500)
    childern = {}
    r = []
    _parent_id = []
    try:
        if request.data.get('rank_name'):
            _ranks = Ranks.objects._mptt_filter(rank_owner=request.user, rank_name=request.data.get('rank_name'))
        else:
            _ranks = Ranks.objects._mptt_filter(rank_owner=request.user)
    except Ranks.DoesNotExist:
        return HttpResponse('جایگاهی برای شما تعریف نشده است.', status=500)
    for _rank in _ranks:
        _parent_id.append(_rank.id)

    if _parent_id == []:
        return HttpResponse('جایگاهی برای شما تعریف نشده است.', status=500)
    else:
        for _rank in _ranks:
            childs = {}
            pids = []
            pids.append(_rank.id)
            for pid in pids:
                for rank in ranks:
                    if rank.tree_id == _rank.tree_id:
                        if pid == rank.parent_id:
                            if rank.rank_owner_id is not None:
                                c = rank.rank_owner_id
                                if c in childs.keys():
                                    pass
                                else:
                                    pic = ("http://185.211.57.73/static/uploads/%s" % rank.rank_owner.image)

                                    # title = rank.rank_owner.first_name + " " + rank.rank_owner.last_name
                                    # slug = slugify(title)
                                    # basename, file_extension = rank.rank_owner.image.split(".")
                                    # new_filename = "%s.%s" % (slug, file_extension)
                                    child = {"rank_name": rank.rank_name, "id": rank.rank_owner.id,
                                             "first_name": rank.rank_owner.first_name,
                                             "last_name": rank.rank_owner.last_name, "mobile": rank.rank_owner.mobile,
                                             "is_legal": rank.rank_owner.is_legal,
                                             # "pic":"http://185.211.57.73/static/uploads/%s" % (rank.rank_owner.image)
                                             "pic": pic
                                             }
                                    r.append(child)
                                    childs[rank.rank_name] = child
                                    child = {}
                            p = rank.id
                            if p in pids:
                                pass
                            else:
                                pids.append(rank.id)
            if request.data.get('rank_name'):
                _rank_ = Ranks.objects.get(rank_owner=request.user, rank_name=request.data.get('rank_name'))
            else:
                _rank_ = Ranks.objects.get(rank_owner=request.user)

            childern["جایگاه"] = _rank_.rank_name
            childern["تعداد کل"] = len(r)
            childern["لیست"] = r
        t = 0
        for i in childern.values():
            if i:
                t += 1
            else:
                t += 0
        if t == 0:
            return HttpResponse('شما زیردستی ندارید.', status=500)
        else:
            return JsonResponse(childern, safe=False)


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
    cred = credentials.Certificate('/opt/w/civil/civilportal.json')

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
        token=token,
    )
    response = messaging.send(message)
    return JsonResponse({'token': token, 'response': response}, encoder=JSONEncoder)


class RepViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Audiences.objects.all()
    serializer_class = AudienceSerializer

    def create(self, request, *args, **kwargs):
        try:
            ppl_id = request.user.id
            session_id = request.data.get('session_id')
            _rep_ppl = Peoples.objects.get(id=request.data.get('rep_ppl'))
            force = self.request.data.get('force')
        except:
            _rep_ppl = None
            session_id = None

        intrposition = []
        myformat = '%Y-%m-%d %H:%M:%S'
        session = Sessions.objects.get(id=session_id)
        sdate = datetime.datetime.strptime(str(session.start_time), myformat).date()
        edate = datetime.datetime.strptime(str(session.end_time), myformat).date()
        stime = datetime.datetime.strptime(str(session.start_time), myformat).time()
        etime = datetime.datetime.strptime(str(session.end_time), myformat).time()

        try:
            _sessions = Sessions.objects.filter(meeting_owner_id=_rep_ppl.id)
        except Sessions.DoesNotExist:
            _sessions = None

        try:
            _audiences = Audiences.objects.filter(people_id=_rep_ppl.id)
        except Audiences.DoesNotExist:
            _audiences = None

        try:
            rep_audiences = Audiences.objects.filter(rep_ppl=_rep_ppl.id)
        except Audiences.DoesNotExist:
            rep_audiences = None

        for _session in _sessions:
            if str(_session.start_time.date()) == str(sdate) or str(_session.end_time.date()) == str(edate):
                if stime <= _session.end_time.time() <= etime or stime <= _session.start_time.time() <= etime:
                    s = {}
                    s["تشکیل دهنده"] = str(
                        _session.meeting_title)
                    intrposition.append(s)
        for _audience in _audiences:
            if str(_audience.session.start_time.date()) == str(sdate) or str(_audience.session.end_time.date()) == str(
                    edate):
                if stime <= _audience.session.end_time.time() <= etime or stime <= _audience.session.start_time.time() <= etime:
                    a = {}
                    a["دعوت شده"] = str(
                        _audience.session.meeting_title)
                    intrposition.append(a)

        for rep_audience in rep_audiences:
            if str(rep_audience.session.start_time.date()) == str(sdate) or str(
                    rep_audience.session.end_time.date()) == str(edate):
                if stime <= rep_audience.session.end_time.time() <= etime or stime <= rep_audience.session.start_time.time() <= etime:
                    r = {}
                    r["جایگزین"] = str(
                        rep_audience.session.meeting_title)
                    intrposition.append(r)

        if intrposition != [] and force == 0:
            return Response(', '.join(map(str, intrposition)) + "تداخل با جلسه:")
        else:
            if Audiences.objects.get(people=ppl_id, session=session_id):
                obj = Audiences.objects.get(people=ppl_id, session=session_id)
                obj.rep_ppl = _rep_ppl
                obj.save()
                try:
                    Seens.objects.get(ppl_id=_rep_ppl.id, sesion_id=session_id)
                except Seens.DoesNotExist:
                    Seens.objects.create(ppl_id=_rep_ppl.id, sesion_id=session_id)

                cred = credentials.Certificate('/opt/w/civil/civilportal.json')
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
