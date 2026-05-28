import logging

from fastapi import FastAPI
from sqladmin import Admin

from admin.auth import AdminAuthBackend
from admin.views import AppMetaAdmin, ParticipantAdmin, RaffleResultAdmin
from config import Config
from db.db_config import sync_engine


logger = logging.getLogger(__name__)


def setup_admin(app: FastAPI, config: Config) -> Admin | None:
    if not config.admin_username or not config.admin_password:
        logger.warning(
            "SQLAdmin is disabled because ADMIN_USERNAME or ADMIN_PASSWORD is not configured."
        )
        return None

    authentication_backend = AdminAuthBackend(
        username=config.admin_username,
        password=config.admin_password,
        secret_key=config.admin_session_secret,
    )
    admin = Admin(
        app=app,
        engine=sync_engine,
        base_url=config.admin_base_url,
        title=config.admin_title,
        authentication_backend=authentication_backend,
    )
    admin.add_view(ParticipantAdmin)
    admin.add_view(RaffleResultAdmin)
    admin.add_view(AppMetaAdmin)
    return admin
