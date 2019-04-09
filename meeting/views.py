# from django.shortcuts import render
#
# # Create your views here.
# from rest_framework import viewsets
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
#
# from .serializers import *
#
#
# class ACViewSet(viewsets.ModelViewSet):
#     permission_classes = (IsAuthenticated,)
#     queryset = Sessions.objects.all()
#     serializer_class = SessionsSerializer
#
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())
#         queryset = queryset.filter(client=self.request.user)
#
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = SessionsSerializer(page, many=True)
#             return self.get_paginated_response(serializer.data)
#
#         serializer = SessionsSerializer(queryset, many=True)
#         return Response(serializer.data)
#
#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         if instance.client == self.request.user:
#             serializer = ACDetailSerializer(instance)
#             return Response(serializer.data)
#         else:
#             return Response(status=status.HTTP_403_FORBIDDEN)
#
#     def create(self, request, *args, **kwargs):
#         items = None
#         if 'items' in request.data:
#             items = request.data.pop('items')
#         serializer = ACCreateSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         obj = serializer.save()
#         # generate_ref_num(self.request, obj, 'ac')
#         obj.client = request.user
#         obj.save()
#         if items:
#             for item in items:
#                 ACItem.objects.create(ac_obj=obj, **item)
#         headers = self.get_success_headers(serializer.data)
#
#         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#
#     def update(self, request, *args, **kwargs):
#         return Response(status=status.HTTP_404_NOT_FOUND)
#
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         if instance.client == self.request.user:
#             # self.perform_destroy(instance)
#             instance.status = 4
#             instance.is_active = False
#             instance.save()
#             return Response(data={'message': 'سفارش با موفقیت لفو شد.'}, status=status.HTTP_204_NO_CONTENT)
#         else:
#             return Response(status=status.HTTP_403_FORBIDDEN)
