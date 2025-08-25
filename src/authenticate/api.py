from exceptions.auth import InvalidOrExpiredToken
from exceptions.users import (
    EmailAlreadyExists,
    PasswordIncorrect,
    PhoneNumberAlreadyExists,
    UserNotFound,
    WeakPasswordError,
)
from utils.router.controller import Controller, api, post, put
from utils.types import AuthenticatedRequest, UnauthenticatedRequest

from .schemas import (
    LoginResponseSchema,
    LoginSchema,
    PasswordChangeRequest,
    PasswordForgetRequest,
    PasswordNewRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterSchema,
    UpdateMeSchema,
    UserSchema,
)
from .services import Service


@api(prefix_or_class="auth", tags=["Authenticate"], auth=None)
class AuthenticateAPI(Controller):
    def __init__(self, service: Service):
        self.service = service

    @post(
        "/register",
        response=LoginResponseSchema,
        exceptions=(EmailAlreadyExists, PhoneNumberAlreadyExists, WeakPasswordError),
    )
    def register(self, request: UnauthenticatedRequest, data: RegisterSchema):
        user, access_token, refresh_token = self.service.register(
            request=request, data=data
        )
        return LoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserSchema.from_orm(user),
        )

    @post("/login", response=LoginResponseSchema)
    def login(self, request: UnauthenticatedRequest, data: LoginSchema):
        user, access_token, refresh_token = self.service.login(
            request=request, email=data.email, password=data.password
        )
        self.logger.info(f"> [LOGIN] {user} - {access_token}")
        return LoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserSchema.from_orm(user),
        )

    @post("/refresh", response=RefreshResponse)
    def refresh(self, request: UnauthenticatedRequest, data: RefreshRequest):
        access_token, refresh_token = self.service.refresh(
            request=request, refresh_token=data.refresh_token
        )
        return RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @put("/logout", auth=True)
    def logout(self, request: AuthenticatedRequest):
        return self.service.logout(request=request)

    @put(
        "/me",
        auth=True,
        response=UserSchema,
        exceptions=(EmailAlreadyExists, PhoneNumberAlreadyExists),
    )
    def update_me(self, request: AuthenticatedRequest, data: UpdateMeSchema):
        return self.service.update_me(user=request.user, data=data)

    @put("password/change", auth=True, response=bool, exceptions=(PasswordIncorrect,))
    def change_password(
        self, request: AuthenticatedRequest, payload: PasswordChangeRequest
    ):
        self.service.change_password(user=request.user, payload=payload)
        return True

    @post("password/forget", response=bool, exceptions=(UserNotFound,))
    def forget_password(self, payload: PasswordForgetRequest):
        self.service.forget_password(email=payload.email)
        return True

    @put("password/reset", response=bool, exceptions=(InvalidOrExpiredToken,))
    def reset_password(self, payload: PasswordNewRequest):
        return self.service.reset_password(payload=payload)
