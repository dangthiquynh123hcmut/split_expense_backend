from http import HTTPStatus

from utils.router.exception import APIException


class UserNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "USER_NOT_FOUND"
    message = "User not found"


class EmailOrPasswordIncorrect(APIException):
    error_code = HTTPStatus.NOT_ACCEPTABLE
    message_code = "EMAIL_OR_PASSWORD_INCORRECT"
    message = "Email or password incorrect"


class PasswordIncorrect(APIException):
    error_code = HTTPStatus.UNAUTHORIZED
    message_code = "PASSWORD_INCORRECT"
    message = "Password incorrect"

class EmailAlreadyExists(APIException):
    error_code = HTTPStatus.CONFLICT
    message_code = "EMAIL_ALREADY_EXISTS"
    message = "Email already exists"

class PhoneNumberAlreadyExists(APIException):
    error_code = HTTPStatus.CONFLICT
    message_code = "PHONE_NUMBER_ALREADY_EXISTS"
    message = "Phone number already exists"


class InvalidEmailFormat(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "INVALID_EMAIL_FORMAT"
    message = "Invalid email format"


class InvalidPhoneNumberFormat(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "INVALID_PHONE_NUMBER_FORMAT"
    message = "Invalid phone number format"


class WeakPasswordError(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "WEAK_PASSWORD"
    
    def __init__(self, message: str = None):
        self.message = message or "Password is too weak"
        super().__init__()
