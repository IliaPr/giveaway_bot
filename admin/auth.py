from hmac import compare_digest

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request


class AdminAuthBackend(AuthenticationBackend):
    def __init__(self, *, username: str, password: str, secret_key: str) -> None:
        super().__init__(secret_key=secret_key)
        self.username = username
        self.password = password

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        if not compare_digest(username, self.username):
            return False
        if not compare_digest(password, self.password):
            return False
        request.session.update({"admin_authenticated": True})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_authenticated"))
