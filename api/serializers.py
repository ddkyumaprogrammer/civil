from rest_framework import serializers
from meeting.models import *



# User = get_user_model()



class PeopleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Peoples
        fields = ('pk', 'first_name', 'last_name', 'username',)


class PlaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Places
        fields = ('place_title','place_address','place_owner', )


class SessionsSerializer(serializers.ModelSerializer):
    class Meta(PeopleSerializer.Meta):
        model = Sessions
        fields = ('meeting_title','meeting_owner','start_time','end_time','place',)


class AudienceSerializer(PeopleSerializer,SessionsSerializer):
    class Meta:
        model = Audiences
        fields = PeopleSerializer.Meta.fields + SessionsSerializer.Meta.fields




#
#
# class SessionsListSerializer(PeopleSerializer):
#     people = PeopleSerializer()
#     class Meta(PeopleSerializer.Meta):
#         model = Sessions
#         fields = PeopleSerializer.Meta.fields + ('meeting_title','owner','start_time','end_time','people','place',)
#
# class SessionsDetailSerializer(PeopleSerializer):
#
#     class Meta(PeopleSerializer.Meta):
#         model = Sessions
#         fields = PeopleSerializer.Meta.fields + ('meeting_title','owner','start_time','end_time','people','place',)
#
# class SessionsCreateSerializer(PeopleSerializer):
#
#     class Meta(PeopleSerializer.Meta):
#         model = Sessions
#         fields = PeopleSerializer.Meta.fields + ('meeting_title','owner','start_time','end_time','people','place',)
