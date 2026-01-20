from uuid import UUID

from ninja import Schema


class AdminResponse(Schema):
    email: str
    uid: UUID
