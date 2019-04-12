from django.contrib import admin
# from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from django_jalali.admin import JDateFieldListFilter
from mptt.admin import MPTTModelAdmin
from .models import *



admin.site.empty_value_display = '(None)'
admin.ModelAdmin.list_per_page = 10
admin.site.register(Audiences)
admin.site.register(Ranks,MPTTModelAdmin)

@admin.register(Places)
class Placesadmin(admin.ModelAdmin):
    list_display = ('place_title','place_owner','place_address',)
    search_fields = ['place_owner','place_owner']
    # list_filter = ('place_title',)


class PlacesInLine(admin.TabularInline):
    model = Places
    extra = 1
    can_delete = True

@admin.register(Peoples)
class Peoplesadmin(admin.ModelAdmin):
    list_display = ('first_name','last_name','mobile','username','is_legal')
    search_fields = ['username','last_name']
    list_filter = ('is_legal',)

    inlines = [
        PlacesInLine
    ]
    def _sessions(self, obj):
        return obj.sessions_set.all().count()
    _sessions.short_description = 'مکان ها'




class AudiencesInLine(admin.TabularInline):
    model = Audiences
    extra = 1
@admin.register(Sessions)
class Sessionsadmin(admin.ModelAdmin):
    list_display = ('meeting_title','start_time','end_time','meeting_owner','place',)
    search_fields = ['meeting_title','start_time',]
    list_filter = (('start_time',JDateFieldListFilter),)
    # list_filter = (('start_time',DateRangeFilter),)

    exclude = ('se_num',)
    inlines = [
        AudiencesInLine
    ]


    def _sessions(self, obj):
        return obj.sessions_set.all().count()
    _sessions.short_description = 'تعداد افراد'





