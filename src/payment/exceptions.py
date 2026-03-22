from http import HTTPStatus

from utils.router.exception import APIException


class PayOSPaymentLinkCreationFailed(APIException):
    error_code = HTTPStatus.INTERNAL_SERVER_ERROR
    message_code = "PAYOS_PAYMENT_LINK_CREATION_FAILED"
    message = "Failed to create PayOS payment link"


class PayOSWebhookVerificationFailed(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "PAYOS_WEBHOOK_VERIFICATION_FAILED"
    message = "PayOS webhook signature verification failed"


class PayOSOrderNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "PAYOS_ORDER_NOT_FOUND"
    message = "PayOS order not found"


class PayOSCancelFailed(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "PAYOS_CANCEL_FAILED"
    message = "Failed to cancel PayOS payment link"
