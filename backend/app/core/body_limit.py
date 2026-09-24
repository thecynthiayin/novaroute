from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


class UploadBodyLimit:
    """Bound multipart bodies, including chunked requests without Content-Length."""

    def __init__(self, app, max_bytes):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/api/upload-resume":
            return await self.app(scope, receive, send)
        consumed = 0
        started = False

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_bytes:
                    raise HTTPException(413, "Upload exceeds size limit")
            return message

        async def tracked_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except HTTPException as exc:
            if started:
                raise
            await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(scope, receive, send)
