import asyncio
import json

import gspread
from gspread.exceptions import WorksheetNotFound

from config import Config
from db.schemas import Participant


class GoogleSheetsClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        has_credentials = bool(
            self.config.google_service_account_file or self.config.google_service_account_json
        )
        return bool(self.config.google_sheet_id and has_credentials)

    async def append_participant(self, participant: Participant) -> None:
        if not self.is_configured:
            raise RuntimeError("Google Sheets integration is not configured.")
        await asyncio.to_thread(self._append_participant_sync, participant)

    def _append_participant_sync(self, participant: Participant) -> None:
        client = self._build_client()
        spreadsheet = client.open_by_key(self.config.google_sheet_id)

        try:
            worksheet = spreadsheet.worksheet(
                self.config.google_worksheet_title)
        except WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=self.config.google_worksheet_title,
                rows=1000,
                cols=10,
            )

        header = [
            "Дата регистрации",
            "ФИО",
            "Телефон",
            "Компания",
            "Должность",
            "Telegram ID",
            "Username",
        ]
        first_row = worksheet.row_values(1)
        if not first_row:
            worksheet.append_row(header, value_input_option="RAW")
        elif first_row[: len(header)] != header:
            worksheet.update(values=[header], range_name="A1:G1", raw=True)

        worksheet.append_row(
            [
                participant.created_at.isoformat(),
                participant.full_name,
                participant.phone,
                participant.company,
                participant.position,
                str(participant.telegram_user_id),
                participant.username or "",
            ],
            value_input_option="USER_ENTERED",
        )

    def _build_client(self) -> gspread.Client:
        if self.config.google_service_account_json:
            credentials_info = json.loads(
                self.config.google_service_account_json)
            return gspread.service_account_from_dict(credentials_info)
        if self.config.google_service_account_file:
            return gspread.service_account(filename=self.config.google_service_account_file)
        raise RuntimeError(
            "Google service account credentials are not configured.")
