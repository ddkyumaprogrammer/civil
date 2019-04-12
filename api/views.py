import datetime
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from drfpasswordless.tasks import refresh_sms_token
from .serializers import *
from django.forms.models import model_to_dict




class SessionsViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Sessions.objects.all().order_by('start_time')
    serializer_class = SessionsSerializer

    def create(self, request, *args, **kwargs):

        serializer = SessionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        obj.meeting_owner = request.user
        obj.save()
        if 'audiences' in request.data:
            audiences = request.data.get('audiences')
            for audience in audiences:
                ppl = Peoples.objects.get(**audience)
                Audiences.objects.create(session=obj, people=ppl)
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
        return JsonResponse([obj.first_name,obj.last_name,obj.is_legal], safe=False)
        # return JsonResponse ({'status':'ok',},encoder=JSONEncoder)


def refresh_sms_token_view(request):
    if not request.user.is_staff:
        return HttpResponse(status=403)

    try:
        eager = refresh_sms_token.apply()
    except Exception as e:
        return HttpResponse(status=500)

    next_url = request.GET.get('next')
    # return redirect('Http://127.0.0.1:8000/admin' + next_url)
    return redirect('Http://127.0.0.1:8000/admin' )



@api_view(['POST'])
def get_childern_view_by_token(request):
    ranks = Ranks.objects.all()
    child = []
    _parent_id = []
    _parent_id.append(Ranks.objects.get(rank_owner_id=request.user.id).id)
    for pid in _parent_id:
            for _rank in ranks:
                if _rank.tree_id == Ranks.objects.get(pk=request.user.id).tree_id:
                    if pid == _rank.parent_id:
                        child.append(_rank.rank_owner_id)
                        _parent_id.append(_rank.id)

    return JsonResponse(child, safe=False)




class PlaceViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Places.objects.all()
    serializer_class = PlaceSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(place_owner=self.request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PlaceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PlaceSerializer(queryset, many=True)
        return Response(serializer.data)





class RepViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Audiences.objects.all()
    serializer_class = AudienceSerializer

    def create(self, request, *args, **kwargs):
        ppl_id = request.user.id
        session_id = request.data.get('session_id' )

        obj = Audiences.objects.get(people =ppl_id,session = session_id)
        rep_ppl_id = Peoples.objects.get(username = request.data.get('rep_ppl'))
        obj.rep_ppl = rep_ppl_id

        obj.save()

        return JsonResponse(model_to_dict(obj), safe=False)

#
#
# class SessionsownerViewSet(viewsets.ModelViewSet):
#     permission_classes = (IsAuthenticated,)
#     queryset = Sessions.objects.all().order_by('start_time')
#     serializer_class = SessionsSerializer
#
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         queryset = queryset.filter(meeting_owner=self.request.user)
#         date = datetime.datetime.strptime(self.request.data.get('start_time'), "%Y-%m-%d")
#
#         # queryset = queryset.filter(start_time__range = ((request.data.get('start_time').format("%Y-%m-%d %H:%M:%S+%f")),(request.data.get('end_time').format("%Y-%m-%d %H:%M:%S+%f"))))
#         queryset = queryset.filter(start_time__range = ("date","1400-09-03"))
#
#         # queryset = queryset.filter(start_time__day=12)
#
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = SessionsSerializer(page, many=True)
#             return self.get_paginated_response(serializer.data)
#
#
#
#         serializer = SessionsSerializer(queryset, many=True)
#         return Response(serializer.data)
