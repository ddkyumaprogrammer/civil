from django.contrib import admin
# from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_jalali.admin import JDateFieldListFilter
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from .models import *


admin.empty_value_display = ''
admin.ModelAdmin.list_per_page = 10


# admin.site.register(Ranks,MPTTModelAdmin)
class MyDraggableMPTTAdmin(DraggableMPTTAdmin):
    def something(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            'rank_name',  # Or whatever you want to put here
        )
    something.short_description = ('something nice')

class RanksInLine(admin.TabularInline):
    model = Ranks.blocked_users.through
    extra = 1
    fk_name = 'from_ranks'
    can_delete = True

admin.site.register(Ranks,
    DraggableMPTTAdmin,
    list_display=(
        'tree_actions',
        'indented_title',
        # 'rank_name',
        'rank_owner',

        # ...more fields if you feel like it...
    ),
    exclude=('blocked_users'),
    list_display_links=(
        'indented_title',
    ),
    raw_id_fields = ('rank_owner', 'parent','extra_parent'
                     ),
    inlines=[RanksInLine]
)
# MPTT_ADMIN_LEVEL_INDENT = 20


@admin.register(Audiences)
class Audiencesadmin(admin.ModelAdmin):
    list_display = ('_stime','session','people','rep_ppl',)
    raw_id_fields = ('people','rep_ppl','session')
    fields =('session','people','rep_ppl',)
    search_fields = ['session__title','people__last_name','rep_ppl__last_name',]

    def _stime(self, obj):
        return obj.session.start_time
    _stime.short_description = 'زمان شروع جلسه'

@admin.register(Places)
class Placesadmin(admin.ModelAdmin):
    list_display = ('place_title','place_owner','place_address',)
    raw_id_fields = ('place_owner',)
    fields = (('place_title','place_owner'),('Longitude','Latitude'),'place_address')
    search_fields = ['place_owner__last_name',]

class PlacesInLine(admin.TabularInline):
    model = Places
    extra = 1
    can_delete = True
@admin.register(Peoples)
class Peoplesadmin(admin.ModelAdmin):
    list_display = ('_peoples','mobile','is_legal','_places')
    fieldsets =(
                (None,{
                     'fields':(('first_name','last_name'),('mobile','is_legal','fcm_token'),('image','_image'))
                }),
                ('بیشتر', {
                            'classes': ('collapse',),
                            'fields': ('username', 'password','is_staff','is_active','date_joined','last_login',
                                           'is_superuser','groups','user_permissions'),
                }),
                )
    search_fields = ['mobile','last_name']
    list_filter = (
        ('is_legal', admin.BooleanFieldListFilter),
    )
    readonly_fields = ('_image',)
    exclude  = ('_image',)
    inlines = [PlacesInLine]
    def _places(self, obj):
        return list(obj.place_owner.all().values_list('place_title', flat=True))
    _places.short_description = 'نام مکان'




class AudiencesInLine(admin.TabularInline):
    model = Audiences
    raw_id_fields = ('people','rep_ppl')
    fields = ('people','seen_people','rep_ppl','seen_rep_ppl')
    readonly_fields =('seen_people','seen_rep_ppl')
    extra = 1
    can_delete = True
    def seen_people(self, obj):
        _session = obj.session.id
        _ppl = obj.people.id
        _seen = Seens.objects.get(ppl_id=_ppl, sesion_id = _session).seen
        return _seen
    def seen_rep_ppl(self, obj):
        _session = obj.session.id
        _rep_ppl = obj.rep_ppl.id
        _seen = Seens.objects.get(ppl_id=_rep_ppl, sesion_id = _session).seen
        return _seen
    seen_people.short_description = 'رویت فرد'
    seen_rep_ppl.short_description = 'رویت جایگزین'

@admin.register(Sessions)
class Sessionsadmin(admin.ModelAdmin):
    list_display = ('meeting_title','start_time','end_time','meeting_owner','place',
                    '_audiences')
    fields = ('meeting_title','meeting_owner',('start_time','end_time'),'place',
              'address', 'Longitude', 'Latitude')
    ordering = ['start_time']
    search_fields = ['meeting_title','start_time','meeting_owner__last_name',]
    list_filter = (('start_time',JDateFieldListFilter),)
    date_hierarchy = 'start_time'

    inlines = [
        AudiencesInLine
    ]

    def _audiences(self, obj):
        first_list = list(obj.session.all().values_list('people__first_name', flat=True))
        last_list = list(obj.session.all().values_list('people__last_name', flat=True))
        _len = obj.session.all().count()
        _list = []
        for i in range(0,_len):
            _list.append(str(first_list[i])+" "+str(last_list[i]))
        return _list
    _audiences.short_description = 'حاضرین'






