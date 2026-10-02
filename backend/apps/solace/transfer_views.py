"""Sensitive, household-scoped account-transfer API."""
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.solace import selectors, services
from apps.solace.serializers import AccountTransferSerializer
from apps.solace.views import SolaceAccessMixin


class AccountTransferListView(SolaceAccessMixin, APIView):
    def get(self, request):
        return Response(AccountTransferSerializer(selectors.list_account_transfers(request.user), many=True).data)

    def post(self, request):
        serializer = AccountTransferSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = services.save_account_transfer(request.user, **serializer.validated_data)
        return Response(AccountTransferSerializer(obj).data, status=201)


class AccountTransferDetailView(SolaceAccessMixin, APIView):
    def patch(self, request, transfer_id):
        obj = selectors.get_account_transfer(request.user, transfer_id)
        if obj is None:
            raise NotFound()
        serializer = AccountTransferSerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = services.save_account_transfer(request.user, obj, **serializer.validated_data)
        return Response(AccountTransferSerializer(obj).data)
