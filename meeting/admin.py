import csv

from django.contrib import admin
# from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from django.http import HttpResponse

from django_jalali.admin import JDateFieldListFilter
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from .models import *
from django.contrib.admin import AdminSite


admin.empty_value_display = '(None)'
_list_per_page = 20
admin.site.register(Audiences)


# admin.site.register(Ranks,MPTTModelAdmin)
class MyDraggableMPTTAdmin(DraggableMPTTAdmin):
    def something(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            'rank_name',  # Or whatever you want to put here
        )
    something.short_description = ('something nice')

admin.site.register(Ranks,
    DraggableMPTTAdmin,
    list_display=(
        'tree_actions',
        'indented_title',
        # 'rank_name',
        'rank_owner',
        'parent',

        # ...more fields if you feel like it...
    ),
    list_display_links=(
        'indented_title',
    ),
)
# MPTT_ADMIN_LEVEL_INDENT = 20


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"



class CivilAdminSite(AdminSite):
    site_header = "Civil Admin"
    site_title = "Civil Admin Portal"
    index_title = "Welcome to Civil Portal"

civil_admin_site = CivilAdminSite(name='civil_admin')

civil_admin_site.empty_value_display = '(None)'
civil_admin_site.register(Audiences)
civil_admin_site.register(Ranks,MPTTModelAdmin)



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

civil_admin_site.register(Places,Placesadmin)




class PlacesInLine(admin.TabularInline):
    model = Places
    extra = 1
    can_delete = True

@admin.register(Peoples)
class Peoplesadmin(admin.ModelAdmin,ExportCsvMixin):
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
    actions = ['export_as_csv']
    def _sessions(self, obj):
        return obj.sessions_set.all().count()
    _sessions.short_description = 'مکان ها'

civil_admin_site.register(Peoples,Peoplesadmin)



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

civil_admin_site.register(Sessions,Sessionsadmin)




