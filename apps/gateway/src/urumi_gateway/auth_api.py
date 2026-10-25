"""REST-only identity surface. MCP authentication is intentionally a later milestone."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, SecretStr, StrictStr, Field, field_validator

from .identity import IdentityError, username, password


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Login(Input):
    username: StrictStr = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)


class Invite(Input):
    username: StrictStr

    @field_validator("username")
    @classmethod
    def name(cls, value):
        return username(value)


class Accept(Input):
    token: SecretStr = Field(max_length=128)
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def secret(cls, value):
        password(value.get_secret_value())
        return value


class KeyInput(Input):
    label: StrictStr = Field(min_length=1, max_length=100)


async def same_origin(request: Request):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        expected = request.app.state.identity.config.origin
        if (request.headers.get("origin") != expected
                or request.headers.get("sec-fetch-site") not in {None, "same-origin", "none"}):
            raise IdentityError("ORIGIN_REJECTED", 403)


async def session(request: Request):
    service = request.app.state.identity
    return await service.authenticate_session(request.cookies.get(service.config.cookie_name))


async def current_user(identity=Depends(session)):
    return identity[0]


async def admin(user=Depends(current_user)):
    from .identity import IdentityService
    IdentityService.require_admin(user)
    return user


def profile(user):
    return {key: user[key] for key in ("id", "username", "role")}


def identity_router(service):
    router = APIRouter(prefix="/api", dependencies=[Depends(same_origin)])

    @router.post("/auth/login")
    async def login(body: Login, request: Request, response: Response):
        user, raw = await service.login(body.username, body.password.get_secret_value())
        # Re-login rotates the browser's existing session rather than leaving it reusable.
        try:
            _, old_id = await service.authenticate_session(request.cookies.get(service.config.cookie_name))
        except IdentityError:
            pass
        else:
            await service.logout(old_id)
        response.set_cookie(service.config.cookie_name, raw, httponly=True, samesite="lax", path="/",
                            secure=service.config.secure_cookie, max_age=service.config.session_seconds)
        return profile(user)

    @router.post("/auth/logout", status_code=204)
    async def logout(identity=Depends(session)):
        await service.logout(identity[1])
        response = Response(status_code=204)
        response.delete_cookie(service.config.cookie_name, path="/", httponly=True,
                               secure=service.config.secure_cookie, samesite="lax")
        return response

    @router.get("/me")
    async def me(user=Depends(current_user)):
        return profile(user)

    @router.post("/invitations", status_code=201)
    async def invite(body: Invite, user=Depends(admin)):
        return await service.invite(user, body.username)

    @router.get("/invitations")
    async def invites(user=Depends(admin)):
        return await service.repo.list_invitations()

    @router.delete("/invitations/{invitation_id}", status_code=204)
    async def revoke_invite(invitation_id: UUID, user=Depends(admin)):
        await service.repo.revoke_invitation(invitation_id, service.clock())
        return Response(status_code=204)

    @router.post("/invitations/accept", status_code=201)
    async def accept(body: Accept):
        return profile(await service.accept(body.token.get_secret_value(), body.password.get_secret_value()))

    @router.post("/keys", status_code=201)
    async def create_key(body: KeyInput, user=Depends(current_user)):
        return await service.create_key(user, body.label)

    @router.get("/keys")
    async def keys(user=Depends(current_user)):
        return await service.repo.list_keys(user["id"])

    @router.delete("/keys/{key_id}", status_code=204)
    async def revoke_key(key_id: UUID, user=Depends(current_user)):
        await service.revoke_key(user, user["id"], key_id)
        return Response(status_code=204)

    @router.get("/users")
    async def users(user=Depends(admin)):
        return await service.repo.list_users()

    @router.get("/users/{user_id}")
    async def detail(user_id: UUID, user=Depends(admin)):
        return await service.repo.user(user_id)

    @router.get("/users/{user_id}/keys")
    async def member_keys(user_id: UUID, user=Depends(admin)):
        await service.repo.user(user_id)
        return await service.repo.list_keys(user_id)

    @router.delete("/users/{user_id}/keys/{key_id}", status_code=204)
    async def admin_revoke(user_id: UUID, key_id: UUID, user=Depends(admin)):
        await service.revoke_key(user, user_id, key_id)
        return Response(status_code=204)

    @router.post("/users/{user_id}/disable")
    async def disable(user_id: UUID, user=Depends(admin)):
        await service.repo.set_member_enabled(user_id, False)
        return await service.repo.user(user_id)

    @router.post("/users/{user_id}/enable")
    async def enable(user_id: UUID, user=Depends(admin)):
        await service.repo.set_member_enabled(user_id, True)
        return await service.repo.user(user_id)

    return router
