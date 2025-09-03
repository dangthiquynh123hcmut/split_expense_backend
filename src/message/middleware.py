from urllib.parse import parse_qs

import jwt
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from authenticate.models import User


class WebSocketJWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        access_token = None

        if "headers" in scope:
            for header_name, header_value in scope["headers"]:
                if header_name == b"authorization":
                    try:
                        scheme, token_value = header_value.decode().split()
                        if scheme.lower() == "bearer":
                            access_token = token_value
                    except (ValueError, UnicodeDecodeError):
                        access_token = None

        if not access_token:
            query_string = scope.get("query_string", b"").decode("utf-8")
            query_params = parse_qs(query_string)
            if "token" in query_params:
                access_token = query_params["token"][0]

        if access_token:
            try:
                payload = jwt.decode(
                    access_token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                user_uid = payload.get("user_uid")
                if user_uid:
                    scope["user"] = await self.get_user(user_uid)
                else:
                    scope["user"] = AnonymousUser()
            except (
                jwt.ExpiredSignatureError,
                jwt.DecodeError,
                jwt.InvalidTokenError,
            ) as e:
                print(f"JWT Error: {str(e)}")
                scope["user"] = AnonymousUser()
        else:
            print("No token provided")
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_uid):
        try:
            return User.objects.get(uid=user_uid)
        except User.DoesNotExist:
            return AnonymousUser()
