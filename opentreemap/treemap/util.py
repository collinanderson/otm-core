# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

import datetime
from collections import OrderedDict

from urlparse import urlparse
from django.shortcuts import get_object_or_404, resolve_url
from django.http import HttpResponse
from django.utils.encoding import force_str, force_text
from django.utils.functional import Promise
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.utils.translation import ugettext_lazy as _
from django.db.models.fields.files import ImageFieldFile
from django.contrib.gis.geos import Point

from opentreemap.util import dict_pop
from treemap.instance import Instance


def safe_get_model_class(model_string):
    """
    In a couple of cases we want to be able to convert a string
    into a valid django model class. For instance, if we have
    'Plot' we want to get the actual class for 'treemap.models.Plot'
    in a safe way.

    This function returns the class represented by the given model
    if it exists in 'treemap.models'
    """
    from treemap.models import MapFeature

    # All of our models live in 'treemap.models', so
    # we can start with that namespace
    models_module = __import__('treemap.models')

    if hasattr(models_module.models, model_string):
        return getattr(models_module.models, model_string)
    elif MapFeature.has_subclass(model_string):
        return MapFeature.get_subclass(model_string)
    else:
        raise ValidationError(
            _('invalid model type: "%s"') % model_string)


def add_visited_instance(request, instance):
    if not (hasattr(request, 'session') and request.session):
        return

    # get the visited instances as a list of tuples, read into
    # OrderedDict. OrderedDict has nice convenience methods for this
    # purpose, but doesn't serialize well, so we pass it through.
    visited_instances = request.session.get('visited_instances', [])
    visited_instances = OrderedDict(visited_instances)

    # delete the existing entry for this instance so it can be
    # reinserted as the most recent entry.
    if instance.pk in visited_instances:
        del visited_instances[instance.pk]

    stamp = datetime.datetime.now().isoformat()
    visited_instances[instance.pk] = stamp

    # turn back into a list of tuples
    request.session['visited_instances'] = visited_instances.items()
    request.session.modified = True


def get_last_visited_instance(request):
    if not hasattr(request, 'session'):
        instance = None
    else:
        visited_instances = request.session.get('visited_instances', [])
        if not visited_instances:
            instance = None
        else:
            # get the first tuple member of the last entry
            # visited_instances have entries '(<pk>, <timestamp>)'
            instance_id = visited_instances[-1][0]
            try:
                instance = Instance.objects.get(pk=instance_id)
            except (Instance.DoesNotExist, MultipleObjectsReturned):
                instance = None

    return instance


def login_redirect(request):
    # Reference: django/contrib/auth/decorators.py
    path = request.build_absolute_uri()
    # urlparse chokes on lazy objects in Python 3, force to str
    resolved_login_url = force_str(
        resolve_url(settings.LOGIN_URL))
    # If the login url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
    current_scheme, current_netloc = urlparse(path)[:2]
    if (not login_scheme or login_scheme == current_scheme)\
    and (not login_netloc or login_netloc == current_netloc):  # NOQA
        path = request.get_full_path()
    from django.contrib.auth.views import redirect_to_login
    return redirect_to_login(
        path, resolved_login_url, REDIRECT_FIELD_NAME)


def get_instance_or_404(**kwargs):
    url_name, found = dict_pop(kwargs, 'url_name')
    if found:
        kwargs['url_name__iexact'] = url_name
    return get_object_or_404(Instance, **kwargs)


def package_field_errors(model_name, validation_error):
    """
    validation_error contains a dictionary of error messages of the form
    {fieldname1: [messages], fieldname2: [messages]}.
    Return a version keyed by "objectname.fieldname" instead of "fieldname".
    """
    dict = {'%s.%s' % (to_object_name(model_name), field): msgs
            for (field, msgs) in validation_error.message_dict.iteritems()}

    return dict


# https://docs.djangoproject.com/en/dev/topics/serialization/#id2
class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, 'as_dict'):
            return obj.as_dict()
        elif isinstance(obj, Point):
            srid = 4326
            obj.transform(srid)
            return {'x': obj.x, 'y': obj.y, 'srid': srid}
        # TODO: Handle S3
        elif isinstance(obj, ImageFieldFile):
            if obj:
                return obj.url
            else:
                return None
        else:
            return super(LazyEncoder, self).default(obj)


def all_subclasses(cls):
    """Return all subclasses of given class"""
    subclasses = set(cls.__subclasses__())
    return subclasses | {clz for s in subclasses for clz in all_subclasses(s)}


def leaf_subclasses(cls):
    """Return all leaf subclasses of given class"""
    all = all_subclasses(cls)
    leaves = {s for s in all if not s.__subclasses__()}
    return leaves


def to_object_name(model_name):
    """BenefitCurrencyConversion -> benefitCurrencyConversion"""
    return model_name[0].lower() + model_name[1:]


def to_model_name(object_name):
    """benefitCurrencyConversion -> BenefitCurrencyConversion"""
    return object_name[0].upper() + object_name[1:]


def get_filterable_audit_models():
    from treemap.models import MapFeature
    map_features = [c.__name__ for c in leaf_subclasses(MapFeature)]
    models = map_features + ['Tree']

    return {model.lower(): model for model in models}


def get_csv_response(filename):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s;' % filename
    response['Cache-Control'] = 'no-cache'

    # add BOM to support CSVs in MS Excel
    # http://en.wikipedia.org/wiki/Byte_order_mark
    response.write(u'\ufeff'.encode('utf8'))
    return response


def get_json_response(filename):
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename=%s;' % filename
    response['Cache-Control'] = 'no-cache'
    return response


def can_read_as_super_admin(request):
    if not hasattr(request.user, 'is_super_admin'):
        return False
    else:
        return request.user.is_super_admin() and request.method == 'GET'
