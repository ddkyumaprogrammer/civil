from django.contrib import admin
# from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from django_jalali.admin import JDateFieldListFilter
from mptt.admin import MPTTModelAdmin
from .models import *



admin.site.empty_value_display = '(None)'
admin.ModelAdmin.list_per_page = 20
admin.site.register(Audiences)
admin.site.register(Ranks,MPTTModelAdmin)


@admin.register(Places)
class Placesadmin(admin.ModelAdmin):
    list_display = ('place_title','place_owner','place_address',)
    fieldsets =(
                (None,{
                     'fields':(('place_title','place_owner'),('Longitude','Latitude'))
                }),
                ('Advanced options', {
                    'classes': ('collapse',),
                    'fields': ('place_address',),
                }),
                )
    search_fields = ['place_owner',]
    # list_filter = ('place_title',)


class PlacesInLine(admin.TabularInline):
    model = Places
    extra = 1
    can_delete = True

@admin.register(Peoples)
class Peoplesadmin(admin.ModelAdmin):
    list_display = ('first_name','last_name','mobile','is_legal')
    fieldsets =(
                (None,{
                     'fields':(('first_name','last_name'),('mobile','is_legal'))
                }),
                ('Advanced options', {
                                'classes': ('collapse',),
                                'fields': ('username', 'password','is_staff','is_active','date_joined','last_login',
                                           'is_superuser','groups','user_permissions'),
                }),
                )
    search_fields = ['mobile','last_name']
    list_filter = (
        ('is_legal', admin.BooleanFieldListFilter),
    )

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
    fieldsets =(
                (None,{
                     'classes': ('wide', 'extrapretty'),
                     'fields':('meeting_title','meeting_owner','place',('start_time','end_time'))
                }),
                )
    ordering = ['start_time']
    search_fields = ['meeting_title','start_time','meeting_owner__last_name',]
    list_filter = (('start_time',JDateFieldListFilter),)
    # list_filter = (('start_time',DateRangeFilter),)

    exclude = ('se_num',)
    inlines = [
        AudiencesInLine
    ]

    def _sessions(self, obj):
        return obj.sessions_set.all().count()
    _sessions.short_description = 'تعداد افراد'





