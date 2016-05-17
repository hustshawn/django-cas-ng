from .cas import CASClient
from django.conf import settings as django_settings
from django.contrib.auth import REDIRECT_FIELD_NAME, SESSION_KEY, BACKEND_SESSION_KEY, load_backend
from django.contrib.auth.models import AnonymousUser
from django.utils.six.moves import urllib_parse


def get_protocol(request):
    """Returns 'http' or 'https' for the request protocol"""
    if request.is_secure():
        return 'https'
    return 'http'


def get_redirect_url(request):
    """Redirects to referring page, or CAS_REDIRECT_URL if no referrer is
    set.
    """

    next_ = request.GET.get(REDIRECT_FIELD_NAME)
    if not next_:
        if django_settings.CAS_IGNORE_REFERER:
            next_ = django_settings.CAS_REDIRECT_URL
        else:
            next_ = request.META.get('HTTP_REFERER', django_settings.CAS_REDIRECT_URL)
        prefix = urllib_parse.urlunparse(
            (get_protocol(request), request.get_host(), '', '', '', ''),
        )
        if next_.startswith(prefix):
            next_ = next_[len(prefix):]
    return next_


def get_service_url(request, redirect_to=None):
    """Generates application django service URL for CAS"""
    protocol = get_protocol(request)
    host = request.get_host()
    service = urllib_parse.urlunparse(
        (protocol, host, request.path, '', '', ''),
    )
    if '?' in service:
        service += '&'
    else:
        service += '?'
    service += urllib_parse.urlencode({
        REDIRECT_FIELD_NAME: redirect_to or get_redirect_url(request)
    })
    return service


def get_cas_client(service_url=None):
    """
    initializes the CASClient according to
    the CAS_* settigs
    """
    return CASClient(
        service_url=service_url,
        version=django_settings.CAS_VERSION,
        server_url=django_settings.CAS_SERVER_URL,
        extra_login_params=django_settings.CAS_EXTRA_LOGIN_PARAMS,
        renew=django_settings.CAS_RENEW,
        username_attribute=django_settings.CAS_USERNAME_ATTRIBUTE,
        proxy_callback=django_settings.CAS_PROXY_CALLBACK
    )


def get_user_from_session(session):
    try:
        user_id = session[SESSION_KEY]
        backend_path = session[BACKEND_SESSION_KEY]
        backend = load_backend(backend_path)
        return backend.get_user(user_id) or AnonymousUser()
    except KeyError:
        return AnonymousUser()


from django.core import urlresolvers
from django.http import HttpResponseRedirect
from django.utils.encoding import force_bytes
import logging

logger = logging.getLogger(__name__)
# Support both Python 2 and Python 3 locations for urllib imports.
try:
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
except ImportError:  # pragma: no cover
    from urllib import urlencode
    from urlparse import parse_qsl, urlparse, urlunparse

def add_query_params(url, params):
    """
    Inject additional query parameters into an existing URL. If
    parameters already exist with the same name, they will be
    overwritten. Parameters with empty values are ignored. Return
    the modified URL as a string.
    """
    def encode(s):
        return force_bytes(s, django_settings.DEFAULT_CHARSET)
    params = dict([(encode(k), encode(v)) for k, v in params.items() if v])

    parts = list(urlparse(url))
    query = dict(parse_qsl(parts[4]))
    query.update(params)
    parts[4] = urlencode(query)
    return urlunparse(parts)

def redirect(to, *args, **kwargs):
    """
    Similar to the Django ``redirect`` shortcut but with altered
    functionality. If an optional ``params`` argument is provided, the
    dictionary items will be injected as query parameters on the
    redirection URL.
    """
    params = kwargs.pop('params', {})
    if params:
        to = add_query_params(to, params)

    logger.debug("Redirecting to %s" % to)
    return HttpResponseRedirect(to)



