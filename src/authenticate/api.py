from exceptions.auth import InvalidOrExpiredOTP, InvalidOrExpiredToken
from exceptions.users import (
    EmailAlreadyExists,
    EmailOrPasswordIncorrect,
    InvalidEmailFormat,
    InvalidPhoneNumberFormat,
    PasswordIncorrect,
    PhoneNumberAlreadyExists,
    UserNotFound,
    WeakPasswordError,
)
from utils.router.controller import Controller, api, get, post, put
from utils.types import AuthenticatedRequest, UnauthenticatedRequest

from .schemas import (
    LoginResponseSchema,
    LoginSchema,
    MeResponseSchema,
    PasswordChangeRequest,
    PasswordForgetRequest,
    PasswordNewRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterSchema,
    ResetPasswordOTPRequest,
    ResetPasswordToken,
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
        exceptions=(
            EmailAlreadyExists,
            PhoneNumberAlreadyExists,
            WeakPasswordError,
            InvalidEmailFormat,
            InvalidPhoneNumberFormat,
        ),
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

    @post(
        "/login", response=LoginResponseSchema, exceptions=(EmailOrPasswordIncorrect,)
    )
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

    @post("/refresh", response=RefreshResponse, exceptions=(InvalidOrExpiredToken,))
    def refresh(self, request: UnauthenticatedRequest, data: RefreshRequest):
        access_token, refresh_token = self.service.refresh(
            request=request, refresh_token=data.refresh_token
        )
        return RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @put("/logout", auth=True, response=bool)
    def logout(self, request: AuthenticatedRequest):
        self.service.logout(request=request)
        return True

    @get("/me", auth=True, response=MeResponseSchema)
    def get_me(self, request: AuthenticatedRequest):
        return self.service.get_me(user=request.user)

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

    @post(
        "password/otp",
        response=ResetPasswordToken,
        exceptions=(
            InvalidOrExpiredOTP,
            UserNotFound,
        ),
    )
    def creat_reset_password_token(self, payload: ResetPasswordOTPRequest):
        return self.service.creat_reset_password_token(payload=payload)

    @put("password/reset", response=bool, exceptions=(InvalidOrExpiredToken,))
    def reset_password(self, payload: PasswordNewRequest):
        return self.service.reset_password(payload=payload)
