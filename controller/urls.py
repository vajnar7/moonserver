from django.conf.urls import url

from controller.views import GetStatus, Move, Ping, GetAstroData, Calibrated, MoveStart, MoveEnd

urlpatterns = [
    url(r'controller/get_status', GetStatus.as_view(), name='get_status'),
    url(r'controller/ping', Ping.as_view(), name='ping'),
    url(r'controller/get_astro_data', GetAstroData.as_view(), name='get_astro_data'),
    url(r'controller/calibrated', Calibrated.as_view(), name='calibrated'),
    url(r'controller/start_move', MoveStart.as_view(), name='move_start'),
    url(r'controller/end_move', MoveEnd.as_view(), name='end_move'),
]
