"""HTTP validation adapters have no dependencies on business or presentation modules."""

from fastapi.routing import APIRoute

from src.core.exceptions import BusinessError, ErrorCode


class ValidatedRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request):
            try:
                return await handler(request)
            except ValueError as exc:
                raise BusinessError(ErrorCode.INVALID_PARAM, str(exc)) from exc

        return guarded
