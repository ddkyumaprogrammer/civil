import os

from django.db import models
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.auth.models import AbstractUser, User
from model_utils.models import TimeStampedModel, TimeFramedModel

from civil import settings
from django_jalali.db import models as jmodels
from meeting.utils import get_image_path


class Peoples(AbstractUser):
    mobile = models.CharField(unique=True, max_length=14, null=True, blank=True, verbose_name='موبایل')
    first_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='نام خانوادگی')
    mobile_verified = models.BooleanField(default=False, verbose_name='موبایل تأیید شده')
    is_legal = models.BooleanField(default=True, verbose_name='شخصیت حقوقی')
    image = models.ImageField(null=True, blank=True,verbose_name='انتخاب عکس', upload_to=get_image_path)
    description = models.TextField(null=True, blank=True, verbose_name='توضیحات')
    MOBILE_FIELD = 'mobile'

    class Meta:
        verbose_name = 'فرد'
        verbose_name_plural = 'افراد'

    def _image(self):
        if self.first_name:
            name = self.first_name + " " + self.last_name
            if self.image:
                # return mark_safe('<img src="%s" style="object-fit:scale-down" width=180 height=240 alt="%s"/>'
                #                  % (("http://127.0.0.1:8001/static/uploads/%s" % (self.image)),name))
                return mark_safe('<img src="%s" width=150 height=200 alt="%s"/>'
                             % (("http://185.211.57.73/static/uploads/%s" % (self.image)), name))
            else:
                return "بدون عکس"
        else:
            return "بدون عکس"
    _image.short_description = 'عکس'
    _image.allow_tags = True

    def _peoples(self):
        return '{} {}'.format(self.first_name, self.last_name)
    _peoples.short_description = 'نام'
    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.username is None:
            self.username = self.mobile
        super().save()
        return


class Places(models.Model):
    place_title = models.CharField(max_length=50,null=True, blank=True, verbose_name='نام ')
    Longitude = models.DecimalField(max_digits=9, decimal_places=6,null=True,blank=True,verbose_name='طول جغرافیای')
    Latitude = models.DecimalField(max_digits=9, decimal_places=6,null=True,blank=True,verbose_name='عرض جغرافیای ')
    place_address = models.TextField(null=True, blank=True, verbose_name='آدرس')
    place_owner = models.ForeignKey(Peoples,null=True, blank=True, verbose_name=' صاحب محل',related_name='place_owner',
                                  on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'محل'
        verbose_name_plural = 'محل ها'

    def __str__(self):
        return '{}'.format(self.place_title)


class Ranks(MPTTModel):
    rank_name = models.CharField(null=True,max_length=50, verbose_name='نام جایگاه')
    rank_owner = models.ForeignKey(Peoples,null=True, blank=True, verbose_name='صاحب جایگاه',related_name='rank_owner',
                                  on_delete=models.CASCADE)
    parent = TreeForeignKey('self',  null=True, blank=True,verbose_name='جایگاه بالا دستی',related_name='childern',
                            db_index=True,on_delete=models.CASCADE)


    class MPTTMeta:
        level_attr = 'mptt_level'
        order_insertion_by = ['rank_name']

    class Meta:
        verbose_name = 'جایگاه'
        verbose_name_plural = 'جایگاه ها'
        ordering = ('rank_name',)

    def __str__(self):
        return self.rank_name

    def delete(self):
        super(Ranks, self).delete()
    delete.alters_data = True

    # def get_absolute_url(self):
    #     return reverse('meeting', kwargs={'path': self.get_path()})



class Sessions (models.Model):
    meeting_title = models.CharField(max_length=50, null=True, blank=True, verbose_name='عنوان')
    meeting_owner = models.ForeignKey(Peoples,null=True, blank=True, verbose_name='برگزارکننده',related_name='meeting_owner',
                                  on_delete=models.CASCADE)
    start_time = jmodels.jDateTimeField(verbose_name='زمان شورع')
    end_time = jmodels.jDateTimeField(verbose_name='زمان خاتمه')
    place = models.ForeignKey(Places,null=True, blank=True, verbose_name='محل تشکیل', related_name='place',
                                  on_delete=models.SET_NULL)
    address = models.CharField(max_length=50, null=True, blank=True, verbose_name='آدرس')
    Longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='طول جغرافیای')
    Latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='عرض جغرافیای ')

    class Meta:
        verbose_name = 'جلسه'
        verbose_name_plural = 'جلسه ها'
        ordering = ('start_time',)

    def __str__(self):
        return '{}'.format(self.meeting_title)

class Seens (models.Model):
    s_rep_ppl = models.BooleanField(default=False, verbose_name="رویت جایگزین")
    s_people = models.BooleanField(default=False, verbose_name="رویت فرد")
    class Meta:
        verbose_name = 'رویت'
        verbose_name_plural = 'رویت ها'


class Audiences (models.Model):
    people = models.ForeignKey(Peoples,null=True, blank=True, verbose_name='دعوت شده', related_name='people',
                                  on_delete=models.SET_NULL)
    seen = models.ForeignKey(Seens,null=True, blank=True, verbose_name="رویت",related_name='seen',
                             on_delete=models.SET_NULL)
    session = models.ForeignKey(Sessions,null=True, blank=True, verbose_name='عنوان جلسه',related_name='session',
                                  on_delete=models.CASCADE)
    rep_ppl = models.ForeignKey(Peoples,null=True, blank=True, verbose_name='جایگزین', related_name='rep_ppl',
                                  on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'حاضرین'
        verbose_name_plural = 'حاضرین'

    def __str__(self):
        return '{} {}'.format(self.people.first_name, self.people.last_name)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        try:
            _seen = Seens.objects.get(id=self.session.id)
        except:
            _seen = Seens.objects.create(id=self.session.id)
        self.seen = _seen
        super().save()
        return
#
