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
            audiences = request.data.get('audiences')
            for audience in audiences:
                r = audience.values()
                for i in r:
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
                _audiences = Audiences.objects.filter(people_id=ppl_id)
            except Audiences.DoesNotExist:
                _audiences = None

            try:
                _rep_ppls = Audiences.objects.filter(rep_ppl_id=ppl_id)
            except Audiences.DoesNotExist:
                _rep_ppls = None

            for _session in _sessions:
                s = {}
                if str(_session.start_time.date()) == str(sdate) or str(_session.end_time.date()) == str(edate):
                    if stime <= _session.end_time.time() <= etime or stime <= _session.start_time.time() <= etime:
                        s[str(_session.meeting_owner.first_name)+' '+str(_session.meeting_owner.last_name)] = str(_session.id)
                        intrposition.append(s)
                        ppl_ower_name.append(_session.meeting_owner.id)
                        ppl_ower_id.append(_session.id)
            for _rep_ppl in _rep_ppls:
                a = {}
                if str(_rep_ppl.session.start_time.date()) == str(sdate) or str(_rep_ppl.session.end_time.date()) == str(
                        edate):
                    if stime <= _rep_ppl.session.end_time.time() <= etime or stime <= _rep_ppl.session.start_time.time() <= etime:
                        a[str(_rep_ppl.people.first_name)+" "+str(_rep_ppl.people.last_name)] = str(_rep_ppl.session.id)
                        intrposition.append(a)
                        ppl_rep_name.append(_rep_ppl.people.id)
                        ppl_rep_id.append(_rep_ppl.session.id)
            for _audience in _audiences:
                k = {}
                if str(_audience.session.start_time.date()) == str(sdate) or str(_audience.session.end_time.date()) == str(
                        edate):
                    if stime <= _audience.session.end_time.time() <= etime or stime <= _audience.session.start_time.time() <= etime:
                        k[str(_audience.people.first_name)+" "+str(_audience.people.last_name)] = str(_audience.session.id)
                        intrposition.append(k)
                        ppl_aud_name.append(_audience.people.id)
                        ppl_aud_id.append(_audience.session.id)

        owner = len(ppl_ower_name)
        aud = len(ppl_aud_name)
        rep = len(ppl_rep_name)
        ppl_ower = []
        ppl_aud = []
        ppl_rep = []
        for i in range(owner):
            w = {}
            w[ppl_ower_name[i]]=ppl_ower_id[i]
            ppl_ower.append(w)
        for i in range(aud):
            w = {}
            w[ppl_aud_name[i]]=ppl_aud_id[i]
            ppl_aud.append(w)
        for i in range(rep):
            w = {}
            w[ppl_rep_name[i]]=ppl_rep_id[i]
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
                obj = serializer.save(meeting_owner = request.user)
                # obj = Sessions.objects.get(meeting_title=request.data.get('title'))
                # obj.meeting_owner = request.user
                # obj.save()
                if 'audiences' in request.data:
                    audiences = request.data.get('audiences')
                    for audience in audiences:
                        try:
                            ppl = Peoples.objects.get(mobile = audience.get('people')).id
                        except Peoples.DoesNotExist:
                            ppl = None
                        try:
                            rppl = Peoples.objects.get(mobile = audience.get('rep_ppl')).id
                        except Peoples.DoesNotExist:
                            rppl = None
                        try:
                            sessn = Sessions.objects.get(id=obj.id).id
                        except Sessions.DoesNotExist:
                            sessn = None
                        Audiences.objects.create(session_id=sessn, people_id=ppl, rep_ppl_id=rppl)

                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)





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
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        _id = request.user.id
        try:
            obj = Peoples.objects.get(id=_id)
        except Peoples.DoesNotExist:
            obj = Peoples.objects.create(id=_id)

        for k,v in request.data.items():
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
            Places.objects.create(place_owner=obj,**place)
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
            return redirect('Http://185.211.57.73/admin/constance/config/' )
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
        return HttpResponse('جایگاهی تعریف نشده است.',status=500)
    childern = {}
    r =[]
    _parent_id = []
    try:
        if request.data.get('rank_name'):
            _ranks =Ranks.objects._mptt_filter(rank_owner=request.user,rank_name = request.data.get('rank_name') )
        else:
            _ranks =Ranks.objects._mptt_filter(rank_owner=request.user)
    except Ranks.DoesNotExist:
        return HttpResponse('جایگاهی برای شما تعریف نشده است.',status=500)
    for _rank in _ranks:
        _parent_id.append(_rank.id)

    if _parent_id == []:
        return HttpResponse('جایگاهی برای شما تعریف نشده است.',status=500)
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
                                    pic = ("http://127.0.0.1:8001/static/uploads/%s" % rank.rank_owner.image)

                                    # title = rank.rank_owner.first_name + " " + rank.rank_owner.last_name
                                    # slug = slugify(title)
                                    # basename, file_extension = rank.rank_owner.image.split(".")
                                    # new_filename = "%s.%s" % (slug, file_extension)
                                    child = {"rank_name":rank.rank_name,"id":rank.rank_owner.id,"first_name":rank.rank_owner.first_name,
                                             "last_name":rank.rank_owner.last_name,"mobile":rank.rank_owner.mobile,
                                             "is_legal":rank.rank_owner.is_legal,
                                             # "pic":"http://185.211.57.73/static/uploads/%s" % (rank.rank_owner.image)
                                                "pic" : pic
                                             }
                                    r.append(child)
                                    childs[rank.rank_name]=child
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

            childern["جایگاه"]=_rank_.rank_name
            childern["تعداد کل"]=len(r)
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


# class PlaceViewSet(viewsets.ModelViewSet):
#     permission_classes = (IsAuthenticated,)
#     queryset = Places.objects.all()
#     serializer_class = PlaceSerializer
#
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         queryset = queryset.filter(place_owner=self.request.user)
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = PlaceSerializer(page, many=True)
#             return self.get_paginated_response(serializer.data)
#
#         serializer = PlaceSerializer(queryset, many=True)
#         return Response(serializer.data)


@api_view(['POST'])
def get_place_by_owner(request):

    obj = []
    try:
        places = Places.objects.filter(place_owner= request.user)
        for place in places:
            obj.append(place)
        leads_as_json = serializers.serialize('json', obj)
        return HttpResponse(leads_as_json, content_type='json')
    except Places.DoesNotExist:
        places = None
        return HttpResponse("مکانی برای شما یافت نشد.")









class RepViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Audiences.objects.all()
    serializer_class = AudienceSerializer

    def create(self, request, *args, **kwargs):
        try:
            ppl_id = request.user.id
            session_id = request.data.get('session_id' )
            rep_ppl_id = Peoples.objects.get(id = request.data.get('rep_ppl'))
            force = self.request.data.get('force')
        except:
            rep_ppl_id = None
            session_id = None


        intrposition = []
        myformat = '%Y-%m-%d %H:%M:%S'
        session = Sessions.objects.get(id = session_id)
        sdate = datetime.datetime.strptime(str(session.start_time), myformat).date()
        edate = datetime.datetime.strptime(str(session.end_time), myformat).date()
        stime = datetime.datetime.strptime(str(session.start_time), myformat).time()
        etime = datetime.datetime.strptime(str(session.end_time), myformat).time()

        try:
            _sessions = Sessions.objects.filter(meeting_owner_id = ppl_id)
        except Sessions.DoesNotExist:
            _sessions = None

        try:
            _audiences = Audiences.objects.filter(people_id = ppl_id)
        except Audiences.DoesNotExist:
            _audiences = None

        try:
            rep_audiences = Audiences.objects.filter(rep_ppl = ppl_id)
        except Audiences.DoesNotExist:
            rep_audiences = None


        for _session in _sessions:
            if str(_session.start_time.date()) == str(sdate) or str(_session.end_time.date()) == str(edate):
                if stime <= _session.end_time.time() <= etime or stime <= _session.start_time.time() <= etime:
                    s = {}
                    s[str(_session.meeting_owner.first_name) + ' ' + str(_session.meeting_owner.last_name)] = str(
                        _session.meeting_title)
                    intrposition.append(s)
        for _audience in _audiences:
            if str(_audience.session.start_time.date()) == str(sdate) or str(_audience.session.end_time.date()) == str(
                    edate):
                if stime <= _audience.session.end_time.time() <= etime or stime <= _audience.session.start_time.time() <= etime:
                    a = {}
                    a[str(_audience.people.first_name) + " " + str(_audience.people.last_name)] = str(
                        _audience.session.meeting_title)
                    intrposition.append(a)


        for rep_audience in rep_audiences:
            if str(rep_audience.session.start_time.date()) == str(sdate) or str(rep_audience.session.end_time.date()) == str(edate):
                if stime <= rep_audience.session.end_time.time() <= etime or stime <= rep_audience.session.start_time.time() <= etime:
                    r = {}
                    r[str(rep_audience.rep_ppl.first_name)+" "+str(rep_audience.rep_ppl.last_name)] = str(
                        rep_audience.session.meeting_title)
                    intrposition.append(r)


        if intrposition != [] and force == 0:
            return Response(', '.join(map(str, intrposition)) +  "تداخل با جلسه:")
        else:
            if Audiences.objects.get(people=ppl_id, session=session_id):
                obj = Audiences.objects.get(people=ppl_id, session=session_id)
                obj.rep_ppl = rep_ppl_id
                obj.save()
                leads_as_json = serializers.serialize('json', [obj, ])
                return HttpResponse(leads_as_json, content_type='json')







@api_view(['POST'])
def  get_sessions_by_date(request):
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
                    s_sessions.append({"as owner":{'id':_session.id , 'meeting_title' : _session.meeting_title,
                    'meeting_owner':str(_session.meeting_owner.first_name)+' '+str(_session.meeting_owner.last_name),
                    'start_time': str(_session.start_time) , 'end_time' : str(_session.end_time)}})

    for _audience in ppl_audiences:
        stime = datetime.datetime.strptime(str(_audience.session.start_time), myformat).date()
        if stime.year == sdate.year and stime.month == sdate.month and stime.day == sdate.day:
                    s_sessions.append({"as audience":{'id':_audience.session.id , 'title' : _audience.session.meeting_title,
                    'meeting_owner':str(_audience.session.meeting_owner.first_name)+' '+str(_audience.session.meeting_owner.last_name),
                                       'start_time': str(_audience.session.start_time) ,'end_time' : str(_session.end_time),
                                       'people' : str(_audience.people.first_name)+" "+str(_audience.people.last_name)}})

    for _audience in rep_audiences:
        stime = datetime.datetime.strptime(str(_audience.session.start_time), myformat).date()
        if stime.year == sdate.year and stime.month == sdate.month and stime.day == sdate.day:
                    s_sessions.append({"as replace":{'id':_audience.session.id , 'title' : _audience.session.meeting_title,
                    'meeting_owner':str(_audience.session.meeting_owner.first_name)+' '+str(_audience.session.meeting_owner.last_name),
                                       'start_time': str(_audience.session.start_time) ,'end_time' : str(_session.end_time),
                                       'people' : str(_audience.rep_ppl.first_name)+" "+str(_audience.rep_ppl.last_name)}})
    return JsonResponse(s_sessions, safe=False)



# class SessionidViewSet(viewsets.ModelViewSet):
#     permission_classes = (IsAuthenticated,)
#     queryset = Sessions.objects.all()
#     serializer_class = SessionsSerializer
#
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         queryset = queryset.filter(meeting_owner=self.request.user)
#         queryset = queryset.filter(id=self.request.data.get('id'))
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = SessionsSerializer(page, many=True)
#             return self.get_paginated_response(serializer.data)
#
#         serializer = SessionsSerializer(queryset, many=True)
#         return Response(serializer.data)

@api_view(['POST'])
def get_session_by_id(request):
    r = {}
    session = []
    try:
        _audiences = Audiences.objects.filter(session_id = request.data.get('id'))
    except Audiences.DoesNotExist:
        _audiences = None
    i=1
    for _audience in _audiences:
        rr = {}
        rr["id"] = _audience.people.id
        rr["first_name"] = _audience.people.first_name
        rr["last_name"] = _audience.people.last_name
        rr["mobile"] = _audience.people.mobile
        rr["is_legal"] = _audience.people.is_legal
        r["No%s"%i] = rr
        i+=1
    try:
        _session = Sessions.objects.get(id=request.data.get('id'))
    except Sessions.DoesNotExist:
        _session = None
    session.append({'id': _session.id, 'meeting_title': str(_session.meeting_title),
                    'meeting_owner': str(_session.meeting_owner.first_name) + '-' +
                    str(_session.meeting_owner.last_name),'start_time': str(_session.start_time),
                     'end_time': str(_session.end_time),'people': str(r)})
    return JsonResponse(session, safe=False)



