import queue

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from moonServer import telescope
from telescope.status_state_machine import user_out, user_in, user_ping


class GetAstroData(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        res = {'data': [
            {'name': "Polaris", 'ra': "2h31m48.704s", 'dec': "+89°15'50.72"},
            {'name': "Vega", 'ra': "18h36m56.332s", 'dec': "+38°47'1.17"},
            {'name': "Aldebaran", 'ra': "4h35m55.237s", 'dec': "+16°30'33.39"},
            {'name': "Sirius", 'ra': "6h45m8.871s", 'dec': "-16°42'57.99"}
        ]}
        return Response(res)


class Calibrated(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        telescope.set_cur_obj(request.data)  # "obj" = "2h31m48.704s +89°15'50.72"
        res = "POS 89°15'50.72 130°15'50.72" # alt az
        user_ping.put(res)
        return Response()


class GetStatus(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        user_out.put("MVST?")
        res = user_in.get()
        return Response(res)


class Move(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        data = request.data
        telescope.calc_steps(data['ra'], data['dec'])
        user_out.put("MV " + telescope.dif_h_steps + " " + telescope.dif_v_steps)
        res = user_in.get()
        # nazaj lahko dobimo: NOT_RDY, MV_ACK
        return Response(res)


class Ping(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            res = user_ping.get(block=True, timeout=1)
        except queue.Empty:
            res = ""
        return Response(res)
