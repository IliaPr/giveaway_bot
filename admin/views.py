from sqladmin import ModelView

from db.models import AppMetaModel, ParticipantModel, RaffleResultModel


class ParticipantAdmin(ModelView, model=ParticipantModel):
    name = "Участник"
    name_plural = "Участники"
    icon = "fa-solid fa-users"
    column_list = [
        ParticipantModel.id,
        ParticipantModel.telegram_user_id,
        ParticipantModel.username,
        ParticipantModel.full_name,
        ParticipantModel.phone,
        ParticipantModel.company,
        ParticipantModel.position,
        ParticipantModel.created_at,
        ParticipantModel.gsheets_synced_at,
        ParticipantModel.gsheets_error,
    ]
    column_searchable_list = [
        ParticipantModel.username,
        ParticipantModel.full_name,
        ParticipantModel.phone,
        ParticipantModel.company,
        ParticipantModel.position,
    ]
    column_sortable_list = [
        ParticipantModel.id,
        ParticipantModel.created_at,
        ParticipantModel.gsheets_synced_at,
    ]
    can_create = False


class RaffleResultAdmin(ModelView, model=RaffleResultModel):
    name = "Результат"
    name_plural = "Результаты"
    icon = "fa-solid fa-trophy"
    column_list = [
        RaffleResultModel.id,
        RaffleResultModel.participant_id,
        RaffleResultModel.prize_code,
        RaffleResultModel.prize_title,
        RaffleResultModel.prize_order,
        RaffleResultModel.created_at,
        RaffleResultModel.notified_at,
    ]
    column_searchable_list = [
        RaffleResultModel.prize_code,
        RaffleResultModel.prize_title,
    ]
    column_sortable_list = [
        RaffleResultModel.id,
        RaffleResultModel.prize_order,
        RaffleResultModel.created_at,
        RaffleResultModel.notified_at,
    ]
    can_create = False


class AppMetaAdmin(ModelView, model=AppMetaModel):
    name = "Метаданные"
    name_plural = "Метаданные"
    icon = "fa-solid fa-gear"
    column_list = [AppMetaModel.key, AppMetaModel.value]
    column_searchable_list = [AppMetaModel.key, AppMetaModel.value]
    can_create = False
