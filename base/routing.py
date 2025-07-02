from django.urls import re_path

from .consumers import *

websocket_urlpatterns = [
    re_path(r"ws/(?P<session_id>\w+)/$", PhishConsumer.as_asgi()),
]