from django.conf.urls import url

from controller.views import GetStatus, Move, Ping, GetAstroData, Calibrated

urlpatterns = [
    url(r'controller/get_status', GetStatus.as_view(), name='get_status'),
    url(r'controller/move', Move.as_view(), name='move'),
    url(r'controller/ping', Ping.as_view(), name='ping'),
    url(r'controller/get_astro_data', GetAstroData.as_view(), name='get_astro_data'),
    url(r'controller/calibrated', Calibrated.as_view(), name='calibrated'),
]
