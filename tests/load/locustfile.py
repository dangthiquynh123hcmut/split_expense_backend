"""
Locust load test — Split Expense Backend

Shared state

run commands
---------
  locust -f tests/load/locustfile.py --host http://localhost:8000

Hoặc headless:
  locust -f tests/load/locustfile.py --host http://localhost:8000 \
         --users 50 --spawn-rate 5 --run-time 2m --headless
"""

from __future__ import annotations

import random
import string
import threading
from datetime import date, timedelta
from typing import TYPE_CHECKING, Optional

from locust import HttpUser, between, task


if TYPE_CHECKING:
    from locust.clients import HttpSession


# ---------------------------------------------------------------------------
# Shared pool — thread-safe storage for cross-user state
# ---------------------------------------------------------------------------


class SharedPool:
    """Thread-safe pool for user / group / event UIDs created during the test."""

    def __init__(self):
        self._lock = threading.Lock()
        self.user_uids: list[str] = []  # registered user UIDs
        self.group_uids: list[str] = []  # created group UIDs
        self.event_uids: list[str] = []  # created event UIDs
        self.friendship_uids: list[str] = []  # pending friend-request UIDs
        self.friend_pairs: set[frozenset] = set()  # globally claimed A↔B pairs

    def add_user(self, uid: str) -> None:
        with self._lock:
            self.user_uids.append(uid)

    def add_group(self, uid: str) -> None:
        with self._lock:
            self.group_uids.append(uid)

    def add_event(self, uid: str) -> None:
        with self._lock:
            self.event_uids.append(uid)

    def add_friendship(self, uid: str) -> None:
        with self._lock:
            self.friendship_uids.append(uid)

    def pop_friendship(self) -> Optional[str]:
        with self._lock:
            return self.friendship_uids.pop(0) if self.friendship_uids else None

    def claim_friend_pair(self, uid_a: str, uid_b: str) -> bool:
        """Atomically claim the pair (uid_a, uid_b). Returns True if claimed,
        False if the pair already exists in either direction."""
        pair = frozenset((uid_a, uid_b))
        with self._lock:
            if pair in self.friend_pairs:
                return False
            self.friend_pairs.add(pair)
            return True

    def pick_unclaimed_target(self, my_uid: str) -> Optional[str]:
        """Return a random user UID that has no existing relationship with my_uid."""
        with self._lock:
            candidates = [
                u
                for u in self.user_uids
                if u != my_uid and frozenset((my_uid, u)) not in self.friend_pairs
            ]
        return random.choice(candidates) if candidates else None

    def random_group_uid(self) -> Optional[str]:
        with self._lock:
            return random.choice(self.group_uids) if self.group_uids else None

    def random_event_uid(self) -> Optional[str]:
        with self._lock:
            return random.choice(self.event_uids) if self.event_uids else None


POOL = SharedPool()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rand_str(k: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=k))


def _rand_phone() -> str:
    """Số điện thoại hợp lệ: 10 chữ số, bắt đầu bằng 0."""
    return "0" + "".join(random.choices(string.digits, k=9))


def _strong_password() -> str:
    """Mật khẩu thoả điều kiện: có hoa, thường, số, ký tự đặc biệt."""
    return (
        "".join(random.choices(string.ascii_uppercase, k=2))
        + "".join(random.choices(string.ascii_lowercase, k=4))
        + "".join(random.choices(string.digits, k=2))
        + "!@"
    )


def _today_str() -> str:
    return date.today().isoformat()


def _future_date_str(days: int = 7) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


class _AuthMixin:
    """
    Mixin cung cấp on_start() chung: đăng ký → đăng nhập → lưu header.
    Subclass phải có self.client (HttpUser).
    """

    if TYPE_CHECKING:
        client: HttpSession

    def _register_and_login(self) -> bool:
        self.email: str = f"{_rand_str(10)}@loadtest.com"
        self.password: str = _strong_password()
        self.phone: str = _rand_phone()
        self.headers: dict = {}
        self.my_uid: str = ""
        self.access_token: str = ""
        self._refresh_token: str = ""

        # --- Register ---
        reg = self.client.post(
            "/api/auth/register",
            json={
                "full_name": f"Locust {_rand_str(4).capitalize()}",
                "email": self.email,
                "password": self.password,
                "phone_number": self.phone,
            },
            name="/api/auth/register",
        )
        if reg.status_code not in (200, 201):
            return False

        payload = reg.json().get("data", {})
        self.access_token = payload.get("access_token", "")
        self._refresh_token = payload.get("refresh_token", "")
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

        # Lấy UID từ profile
        me = self.client.get("/api/auth/me", headers=self.headers, name="/api/auth/me")
        if me.status_code == 200:
            uid = me.json().get("data", {}).get("uid", "")
            if uid:
                self.my_uid = uid
                POOL.add_user(uid)
        return bool(self.access_token)


class ReadOnlyUser(HttpUser, _AuthMixin):
    host = "http://localhost:8000"
    wait_time = between(1, 2)

    def on_start(self):
        self._register_and_login()

    @task(4)
    def list_groups(self):
        self.client.get(
            "/api/groups?page=1&page_size=10&name=&order_by=updated_at",
            headers=self.headers,
            name="/api/groups (list)",
        )

    @task(3)
    def list_friends(self):
        self.client.get(
            "/api/friends?page=1&page_size=10&search=&order_by=full_name",
            headers=self.headers,
            name="/api/friends (list)",
        )

    @task(3)
    def get_wallet(self):
        self.client.get("/api/wallet", headers=self.headers, name="/api/wallet")

    @task(2)
    def get_wallet_external_transactions(self):
        self.client.get(
            "/api/wallet/external?page=1&page_size=10",
            headers=self.headers,
            name="/api/wallet/external",
        )

    @task(2)
    def get_group_detail(self):
        uid = POOL.random_group_uid()
        if not uid:
            return
        with self.client.get(
            f"/api/groups/{uid}",
            headers=self.headers,
            name="/api/groups/{uid}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (
                200,
                403,
            ):  # 403 = not a member, expected for random pool groups
                resp.success()

    @task(1)
    def list_friend_requests_received(self):
        self.client.get(
            "/api/friends/request?page=1&page_size=10&request_type=Received&search=&order_by=full_name",
            headers=self.headers,
            name="/api/friends/request (Received)",
        )


class FriendFlowUser(HttpUser, _AuthMixin):
    host = "http://localhost:8000"
    wait_time = between(2, 4)

    def on_start(self):
        self._register_and_login()

    @task(3)
    def send_friend_request(self):
        # pick_unclaimed_target filters both directions atomically in POOL
        target = POOL.pick_unclaimed_target(self.my_uid)
        if not target:
            return
        # Atomically claim before sending — prevents the reverse-direction 409
        if not POOL.claim_friend_pair(self.my_uid, target):
            return
        resp = self.client.post(
            "/api/friends/request",
            json={"receiver_uid": target, "message": "Xin chào! Kết bạn nhé."},
            headers=self.headers,
            name="/api/friends/request (send)",
        )
        if resp.status_code in (200, 201):
            pass  # receiver will accept via their own received-requests fetch
        elif resp.status_code == 409:
            # Race condition slipped through — record success to keep stats clean
            resp.success() if hasattr(resp, "success") else None

    @task(2)
    def accept_friend_request(self):
        # Fetch this user's own received requests — avoids shared-pool drain / wrong-user 403
        list_resp = self.client.get(
            "/api/friends/request?page=1&page_size=5&request_type=Received&search=&order_by=full_name",
            headers=self.headers,
            name="/api/friends/request (Received)",
        )
        if list_resp.status_code != 200:
            return
        items = list_resp.json().get("data", {}).get("items", [])
        if not items:
            return
        friendship_uid = items[0].get("friendship_uid", "")
        if not friendship_uid:
            return
        self.client.put(
            f"/api/friends/{friendship_uid}/accept",
            headers=self.headers,
            name="/api/friends/{uid}/accept",
        )

    @task(4)
    def list_friends(self):
        self.client.get(
            "/api/friends?page=1&page_size=10&search=&order_by=full_name",
            headers=self.headers,
            name="/api/friends (list)",
        )

    @task(1)
    def list_received_requests(self):
        self.client.get(
            "/api/friends/request?page=1&page_size=10&request_type=Received&search=&order_by=full_name",
            headers=self.headers,
            name="/api/friends/request (Received)",
        )


class FullFlowUser(HttpUser, _AuthMixin):
    host = "http://localhost:8000"
    wait_time = between(2, 6)

    def on_start(self):
        self._register_and_login()
        self.my_group_uid: Optional[str] = None
        self.my_event_uid: Optional[str] = None
        self.my_expense_uids: list[str] = []
        # Khởi tạo một nhóm ngay khi bắt đầu
        self._setup_group()

    # ------------------------------------------------------------------
    # Setup helpers (không tính là task)
    # ------------------------------------------------------------------

    def _setup_group(self):
        members: list[str] = []
        for _ in range(3):
            with POOL._lock:
                candidates = [
                    u for u in POOL.user_uids if u != self.my_uid and u not in members
                ]
            uid = random.choice(candidates) if candidates else None
            if uid:
                members.append(uid)

        resp = self.client.post(
            "/api/groups",
            json={
                "name": f"FullFlow-{_rand_str(5).upper()}",
                "list_user_uids": members,
            },
            headers=self.headers,
            name="/api/groups (create)",
        )
        if resp.status_code in (200, 201):
            uid = resp.json().get("data", {}).get("uid", "")
            if uid:
                self.my_group_uid = uid
                POOL.add_group(uid)

    def _setup_event(self) -> Optional[str]:
        # Never fall back to a random pool group — user must be a member (CreateIsDenied)
        if not self.my_group_uid:
            return None

        # Fetch group members to invite — exclude self to avoid duplicate EventMember
        # Backend always adds creator separately, so invite_uids must NOT include self
        members_resp = self.client.get(
            f"/api/groups/{self.my_group_uid}/members?page=1&page_size=20&search=&order_by=full_name",
            headers=self.headers,
            name="/api/groups/{uid}/members",
        )
        invite_uids: list[str] = []
        if members_resp.status_code == 200:
            items = members_resp.json().get("data", {}).get("items", [])
            for item in items[:3]:
                uid = item.get("uid", "")
                if uid and uid != self.my_uid:
                    invite_uids.append(uid)

        # Store the exact event member UIDs (invite_uids + creator added by backend)
        # This must match list_expense_member exactly when creating expenses
        self.my_event_member_uids: list[str] = invite_uids + (
            [self.my_uid] if self.my_uid else []
        )

        resp = self.client.post(
            "/api/events",
            json={
                "name": f"Event-{_rand_str(5).capitalize()}",
                "group_id": self.my_group_uid,
                "description": "Sự kiện tải thử nghiệm",
                "event_start": _today_str(),
                "event_end": _future_date_str(7),
                "list_user_uid": invite_uids,  # [] is fine; None → uid__in=None → 500
            },
            headers=self.headers,
            name="/api/events (create)",
        )
        if resp.status_code in (200, 201):
            uid = resp.json().get("data", {}).get("uid", "")
            if uid:
                self.my_event_uid = uid
                POOL.add_event(uid)
                return uid
        return None

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task(2)
    def create_event_and_expense(self):
        """Tạo sự kiện mới rồi tạo chi phí trong sự kiện đó."""
        event_uid = self._setup_event()
        if not event_uid:
            return

        # Use the exact event member list stored during _setup_event
        # list_expense_member count MUST equal event member count (ListMemberNotMatch → 400)
        members = getattr(
            self, "my_event_member_uids", [self.my_uid] if self.my_uid else []
        )
        if not members:
            return

        total = random.randint(50_000, 500_000)
        per_person = round(total / len(members), 2)
        expense_members = [{"user_uid": uid, "amount": per_person} for uid in members]

        resp = self.client.post(
            "/api/expenses",
            json={
                "event_uid": event_uid,
                "name": f"Chi phí {_rand_str(4)}",
                "total_amount": total,
                "currency": "VND",
                "split_type": "EQUAL",
                "paid_by": self.my_uid,
                "expense_date": _today_str()
                + "T00:00:00",  # required non-nullable field — omitting → IntegrityError → 500
                "list_expense_member": expense_members,
            },
            headers=self.headers,
            name="/api/expenses (create)",
        )
        if resp.status_code in (200, 201):
            uid = resp.json().get("data", {}).get("uid", "")
            if uid:
                self.my_expense_uids.append(uid)

    @task(3)
    def view_group_detail(self):
        uid = self.my_group_uid
        if not uid:
            return
        self.client.get(
            f"/api/groups/{uid}",
            headers=self.headers,
            name="/api/groups/{uid}",
        )

    @task(3)
    def view_expense_detail(self):
        if not self.my_expense_uids:
            return
        uid = random.choice(self.my_expense_uids)
        self.client.get(
            f"/api/expenses/{uid}",
            headers=self.headers,
            name="/api/expenses/{uid}",
        )

    @task(2)
    def list_my_groups(self):
        self.client.get(
            "/api/groups?page=1&page_size=10&name=&order_by=updated_at",
            headers=self.headers,
            name="/api/groups (list)",
        )

    @task(1)
    def soft_delete_expense(self):
        if not self.my_expense_uids:
            return
        uid = self.my_expense_uids.pop()
        self.client.put(
            f"/api/expenses/{uid}/soft",
            headers=self.headers,
            name="/api/expenses/{uid}/soft",
        )

    @task(2)
    def view_event_detail(self):
        uid = self.my_event_uid or POOL.random_event_uid()
        if not uid:
            return
        self.client.get(
            f"/api/events/{uid}",
            headers=self.headers,
            name="/api/events/{uid}",
        )

    @task(1)
    def send_message_to_group(self):
        uid = self.my_group_uid or POOL.random_group_uid()
        if not uid:
            return
        self.client.post(
            f"/api/messages/group/{uid}",
            json={"content": f"Tin nhắn thử nghiệm {_rand_str(6)}"},
            headers=self.headers,
            name="/api/messages/group/{uid} (send)",
        )

    @task(1)
    def list_group_messages(self):
        uid = self.my_group_uid or POOL.random_group_uid()
        if not uid:
            return
        self.client.get(
            f"/api/messages/group/{uid}?page=1&page_size=20",
            headers=self.headers,
            name="/api/messages/group/{uid} (list)",
        )
