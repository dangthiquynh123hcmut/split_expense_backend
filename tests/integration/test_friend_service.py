"""
Integration tests for friend.services.FriendService.

Covers: sending friend requests, accepting, removing/rejecting, and error cases.
FCM and notification writes are mocked.
"""

import uuid

import pytest

from exceptions.friends import FriendHasRelation, FriendshipNotFound
from exceptions.users import UserNotFound
from friend.models import Friend
from friend.schemas.request import AddFriendRequest
from friend.services import FriendService


def _make_service():
    return FriendService()


@pytest.mark.django_db
class TestSendFriendRequest:
    def test_creates_pending_friendship(
        self, user_a, user_b, mock_fcm, mock_notification
    ):
        service = _make_service()
        service.send_friend_request(
            user=user_a,
            data=AddFriendRequest(receiver_uid=user_b.uid, message="Hi!"),
        )
        friendship = Friend.objects.filter(user=user_a, friend=user_b).first()
        assert friendship is not None
        assert friendship.status == "PENDING"

    def test_message_is_stored(self, user_a, user_b, mock_fcm, mock_notification):
        service = _make_service()
        service.send_friend_request(
            user=user_a,
            data=AddFriendRequest(receiver_uid=user_b.uid, message="Let's connect"),
        )
        friendship = Friend.objects.get(user=user_a, friend=user_b)
        assert friendship.message_request == "Let's connect"

    def test_sending_to_nonexistent_user_raises(
        self, user_a, mock_fcm, mock_notification
    ):
        service = _make_service()
        with pytest.raises(UserNotFound):
            service.send_friend_request(
                user=user_a,
                data=AddFriendRequest(receiver_uid=uuid.uuid4(), message=None),
            )

    def test_sending_to_self_raises(self, user_a, mock_fcm, mock_notification):
        service = _make_service()
        with pytest.raises(FriendHasRelation):
            service.send_friend_request(
                user=user_a,
                data=AddFriendRequest(receiver_uid=user_a.uid, message=None),
            )

    def test_duplicate_request_raises(
        self, user_a, user_b, mock_fcm, mock_notification
    ):
        service = _make_service()
        service.send_friend_request(
            user=user_a,
            data=AddFriendRequest(receiver_uid=user_b.uid, message=None),
        )
        with pytest.raises(FriendHasRelation):
            service.send_friend_request(
                user=user_a,
                data=AddFriendRequest(receiver_uid=user_b.uid, message=None),
            )

    def test_reverse_request_also_raises(
        self, user_a, user_b, mock_fcm, mock_notification
    ):
        """If user_a already sent a request to user_b, user_b cannot send one back."""
        service = _make_service()
        service.send_friend_request(
            user=user_a,
            data=AddFriendRequest(receiver_uid=user_b.uid, message=None),
        )
        with pytest.raises(FriendHasRelation):
            service.send_friend_request(
                user=user_b,
                data=AddFriendRequest(receiver_uid=user_a.uid, message=None),
            )


@pytest.mark.django_db
class TestAcceptFriendRequest:
    def _create_pending(self, requester, receiver):
        return Friend.objects.create(
            user=requester,
            friend=receiver,
            status="PENDING",
        )

    def test_accept_request_changes_status_to_accepted(
        self, user_a, user_b, mock_fcm, mock_notification
    ):
        friendship = self._create_pending(user_a, user_b)
        service = _make_service()
        service.accept_request_friend(friendship_uid=friendship.uid)
        friendship.refresh_from_db()
        assert friendship.status == "ACCEPTED"

    def test_accept_nonexistent_friendship_raises(self, mock_fcm, mock_notification):
        service = _make_service()
        with pytest.raises(FriendshipNotFound):
            service.accept_request_friend(friendship_uid=uuid.uuid4())


@pytest.mark.django_db
class TestRemoveOrRejectFriend:
    def test_remove_accepted_friendship(self, user_a, user_b):
        friendship = Friend.objects.create(
            user=user_a, friend=user_b, status="ACCEPTED"
        )
        service = _make_service()
        service.remove_or_reject_friend(friendship_uid=friendship.uid)
        assert not Friend.objects.filter(uid=friendship.uid).exists()

    def test_reject_pending_request(self, user_a, user_b):
        friendship = Friend.objects.create(user=user_a, friend=user_b, status="PENDING")
        service = _make_service()
        service.remove_or_reject_friend(friendship_uid=friendship.uid)
        assert not Friend.objects.filter(uid=friendship.uid).exists()

    def test_remove_nonexistent_friendship_raises(self):
        service = _make_service()
        with pytest.raises(FriendshipNotFound):
            service.remove_or_reject_friend(friendship_uid=uuid.uuid4())
