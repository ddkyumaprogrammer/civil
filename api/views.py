import datetime
import json

import jdatetime
from django.shortcuts import redirect, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
# from drfpasswordless.tasks import refresh_sms_token
from .serializers import *
from .tasks import refresh_sms_token
from django.forms.models import model_to_dict
from meeting.models import *



class SessionsViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Sessions.objects.all().order_by('start_time')
    serializer_class = SessionsSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(data=request.data, context={'request': request})
        _sessions = Sessions.objects.all()
        # obj = serializer.save()
        intrposition = []
        myformat = '%Y-%m-%d %H:%M:%S'
        sdate = datetime.datetime.strptime(str(self.request.data.get('start_time')), myformat).date()
        edate = datetime.datetime.strptime(str(self.request.data.get('end_time')), myformat).date()
        stime = datetime.datetime.strptime(str(self.request.data.get('start_time')), myformat).time()
        etime = datetime.datetime.strptime(str(self.request.data.get('end_time')), myformat).time()
        force = self.request.data.get('force')
        for _session in _sessions:
            if str(_session.start_time.date())== str(sdate) or str(_session.end_time.date())== str(edate):
                if stime <= _session.end_time.time() <= etime or stime <= _session.start_time.time() <= etime:
                    intrposition.append(_session)
                    # goli = Sessions.objects.filter(end_time__range =(sdate , edate))


        if intrposition != [] and force == 0:
            return Response( ', '.join(map(str, intrposition))+"--"+"تداخل با جلسه")


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
                        except :
                            ppl = None
                        try:
                            rppl = Peoples.objects.get(mobile = audience.get('rep_ppl')).id
                        except :
                            rppl = None
                        sessn = Sessions.objects.get(id = obj.id).id
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
        if _id:
            obj=Peoples.objects.get(id=_id)
        else:
            obj=Peoples.objects.create(id=_id)
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

    try:
        # eager = refresh_sms_token.apply()
        ea = refresh_sms_token()
    except Exception as e:
        return HttpResponse(status=500)


    # next_url = request.GET.get('next')
    # return redirect('Http://127.0.0.1:8000/admin/constance/config/')
    return redirect('Http://185.211.57.73/admin/constance/config/' )



@api_view(['POST'])
def get_childern_view_by_token(request):
    try:
        ranks = Ranks.objects.all()
    except Ranks.DoesNotExist:
        return HttpResponse('جایگاهی برای شما تعریف نشده است.',status=500)
    childern = {}
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
                                    child = []
                                    child.append(rank.rank_owner.first_name)
                                    child.append(rank.rank_owner.last_name)
                                    child.append(rank.rank_owner.mobile)
                                    child.append(rank.rank_owner.is_legal)
                                    childs[rank.rank_owner.pk]=child
                            p = rank.id
                            if p in pids:
                                pass
                            else:
                                pids.append(rank.id)
            childern[_rank.rank_name] = childs
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
    places = Places.objects.filter(place_owner= request.user)
    for place in places:
        obj.append(place)
    leads_as_json = serializers.serialize('json',  obj)
    return HttpResponse(leads_as_json, content_type='json')








class RepViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Audiences.objects.all()
    serializer_class = AudienceSerializer

    def create(self, request, *args, **kwargs):

        ppl_id = request.user.id
        session_id = request.data.get('session_id' )

        obj = Audiences.objects.get(people =ppl_id,session = session_id)
        rep_ppl_id = Peoples.objects.get(id = request.data.get('rep_ppl'))
        obj.rep_ppl = rep_ppl_id

        obj.save()
        leads_as_json = serializers.serialize('json', [obj, ])
        return HttpResponse(leads_as_json, content_type='json')


        # return JsonResponse(model_to_dict(obj), safe=False)





@api_view(['POST'])
def  get_sessions_by_owner(request):
    # sdate = jalali.Persian(request.data.get('s_time')).gregorian_datetime()
    sdate = datetime.datetime.strptime(request.data.get('time'), "%Y-%m-%d")
    s_sessions = []

    _sessions = Sessions.objects.filter(meeting_owner=request.user)
    for _session in _sessions:
        stime = datetime.datetime.strptime(str(_session.start_time), '%Y-%m-%d %H:%M:%S%z').date()
        if stime.year == sdate.year:
            if stime.month == sdate.month:
                if stime.day == sdate.day:
                    s_sessions.append({'id':_session.id , 'meeting_title' : _session.meeting_title,
                    'meeting_owner':str(_session.meeting_owner.first_name)+'-'+str(_session.meeting_owner.last_name),
                    'start_time': str(_session.start_time) , 'end_time' : str(_session.end_time), 'people' : ""})

    _audiences = Audiences.objects.all()
    for _audience in _audiences:
        sstime = datetime.datetime.strptime(str(_audience.session.start_time), '%Y-%m-%d %H:%M:%S%z').date()
        if sstime.year == sdate.year:
            if sstime.month == sdate.month:
                if sstime.day == sdate.day:
                    s_sessions.append({'id':_audience.session.id , 'title' : _audience.session.meeting_title,
                    'meeting_owner':str(_audience.session.meeting_owner.first_name)+'-'+str(_audience.session.meeting_owner.last_name),
                                       'start_time': str(_audience.session.start_time) , 'people' : str(_audience.people.first_name)+str(_audience.people.last_name)})

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

from django.core import serializers
@api_view(['POST'])
def get_session_by_id(request):
    obj = Sessions.objects.get(id = request.data.get('id'))

    # obj = model_to_dict(obj)
    # print(obj)
    # def myconverter(o):
    #     if isinstance(o,jdatetime.datetime):
    #         return o.__str__()
    # result = json.dumps(obj,default=myconverter )
    # return Response(result.encode('utf-8'))


    leads_as_json = serializers.serialize('json',  [ obj, ])
    return HttpResponse(leads_as_json, content_type='json')

