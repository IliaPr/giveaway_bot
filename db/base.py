from datetime import datetime
from typing import Union, List, TypeVar, Optional, Type

import bcrypt
from sqladmin import ModelView, action
from sqlalchemy import Date, DateTime, and_, extract, func, select, desc, asc, cast, or_, String, Alias
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from starlette.requests import Request
from starlette.responses import RedirectResponse

from db.db_config import SyncSession


class BaseModel:
    T = TypeVar("T", bound="BaseModel")

    @classmethod
    async def create(cls, session: AsyncSession, data: dict) -> Union[int, str]:
        """
        Функция создания записи в базе данных
        :param session:
        :param data:
        :return:
        """
        try:
            new_record = cls(**data)
            session.add(new_record)
            await session.commit()
            await session.refresh(new_record)
            return new_record.id
        except IntegrityError as e:
            return "Error in creating record: " + str(e)

    @classmethod
    async def get(cls, session: AsyncSession, id: int) -> Union[dict, None]:
        """
        Функция получения записи из базы данных по ID
        :param session:
        :param id:
        :return:
        """
        record = await session.get(cls, id)
        if record:
            return record.__dict__
        else:
            return None

    @classmethod
    async def update(
        cls, session: AsyncSession, id: int, data: dict
    ) -> Union[str, None]:
        """
        Функция обновления записи в базе данных
        :param session:
        :param id:
        :param data:
        :return:
        """
        record = await session.get(cls, id)
        if not record:
            return f"Record with id {id} does not exist"

        for key, value in data.items():
            if value is not None:
                # Обрабатываем обновление пароля отдельно
                if key == "password":
                    hashed_password = bcrypt.hashpw(
                        value.encode(), bcrypt.gensalt())
                    value = hashed_password.decode()
                setattr(record, key, value)

        try:
            await session.commit()
            await session.refresh(record)
        except IntegrityError as e:
            return "Error in updating record: " + str(e)

        return None

    @classmethod
    async def delete(cls, session: AsyncSession, id: int) -> Union[str, None]:
        """
        Функция удаления записи из базы данных
        :param session:
        :param id:
        :return:
        """
        record = await session.get(cls, id)
        if not record:
            return f"Record with id {id} does not exist"

        try:
            await session.delete(record)
            await session.commit()
        except Exception as e:
            return "Error in deleting record: " + str(e)

        return None

    @classmethod
    async def get_all(cls, session: AsyncSession) -> List[dict]:
        """
        Функция получения всех записей из базы данных
        :param session:
        :return:
        """
        records = await session.execute(select(cls))
        return [record.__dict__ for record in records.scalars().all()]

    @classmethod
    async def check_existence(cls, session: AsyncSession, model, id: int) -> bool:
        """
        Функция проверяет существование записи в базе данных по заданному ID
        Args:
        session (Session): Сессия подключения к базе данных.
        model: Класс модели SQLAlchemy, для которой проверяется существование записи.
        id (int): ID записи для проверки
        Returns:
        bool: Возвращает True, если запись существует, иначе False.
        """
        stmt = select(model).filter(model.id == id)
        result = await session.execute(stmt)
        return result.scalars().first() is not None

    @classmethod
    async def check_existence_by_kwargs(cls, session: AsyncSession, **kwargs) -> bool:
        """
        Функция проверяет существование записи в базе данных по заданным параметрам
        Args:
        session (Session): Сессия подключения к базе данных.
        model: Класс модели SQLAlchemy, для которой проверяется существование записи.
        **kwargs: Параметры для проверки
        Returns:
        bool: Возвращает True, если запись существует, иначе False.
        """
        stmt = select(cls).filter_by(**kwargs)
        result = await session.execute(stmt)
        record = result.scalars().first()
        if record:
            return True
        return False

    @classmethod
    async def get_by_kwargs(
        cls, session: AsyncSession, multiple: bool = False, **kwargs,
    ) -> Optional["BaseModel"] | List["BaseModel"]:
        """
        Функция получает запись из базы данных по заданным параметрам
        Args:
        session (Session): Сессия подключения к базе данных.
        model: Класс модели SQLAlchemy, для которой проверяется существование записи.
        multiple: bool Вернуть несколько записей
        **kwargs: Параметры для проверки
        Returns:

        """
        stmt = select(cls).filter_by(**kwargs)
        result = await session.execute(stmt)
        if multiple:
            record = result.scalars().all()
        else:
            record = result.scalars().first()
        if record:
            return record
        return None

    @classmethod
    def get_by_kwargs_sync(cls, session: SyncSession, **kwargs):
        """
        Функция получает запись из базы данных по заданным параметрам
        Args:
        session (Session): Сессия подключения к базе данных.
        model: Класс модели SQLAlchemy, для которой проверяется существование записи.
        **kwargs: Параметры для проверки
        Returns:
        """
        stmt = select(cls).filter_by(**kwargs)
        result = session.execute(stmt)
        record = result.scalars().first()
        if record:
            return record
        return None

    @classmethod
    async def get_or_create(cls, session: AsyncSession, **kwargs) -> "BaseModel":
        """
        Функция получает запись из базы данных по заданным параметрам
        Args:
        session (Session): Сессия подключения к базе данных.
        model: Класс модели SQLAlchemy, для которой проверяется существование записи.
        **kwargs: Параметры для проверки
        Returns:
        bool: Возвращает True, если запись существует, иначе False.
        """
        record = await cls.get_by_kwargs(session, **kwargs)
        if record:
            return record
        else:
            await cls.create(session, **kwargs)
            new_record: cls = await cls.get_by_kwargs(session, **kwargs)
            return new_record


class BaseAdminView(ModelView):
    # Настройки для поиска или фильтрации по вложенным полям. Ключ указывает на название внешнего ключа,
    # значение на его поле, по которому будет происходить сортировка.
    filter_fields: dict = {}
    # Массив прав, которые должен иметь пользователь
    _required_roles: list = []
    can_edit = False
    can_delete = False
    can_create = False
    can_export = False
    can_view_details = False
    page_size = 100
    page_size_options = [10, 25, 50, 100, 250, 500, 1000]

    @property
    def required_roles(self) -> list:
        """
        Динамически получает все доступные роли из базы данных
        """
        if self._required_roles:
            return self._required_roles

        # Получаем все роли из базы данных
        try:
            from db.models import Group
            with SyncSession() as session:
                return [g.name for g in session.query(Group).all()]
        except Exception as e:
            # В случае ошибки возвращаем пустой список (доступ для всех)
            print(f"Ошибка при получении ролей: {e}")
            return []

    @required_roles.setter
    def required_roles(self, value: list):
        """
        Позволяет устанавливать конкретные роли, если нужно ограничить доступ
        """
        self._required_roles = value

    def enable_access_for_all_roles(self):
        """
        Включает доступ для всех ролей в системе (динамически)
        """
        self._required_roles = []

    def restrict_access_to_roles(self, roles: list):
        """
        Ограничивает доступ только указанным ролям
        """
        self._required_roles = roles

    def apply_permissions(self, permissions):
        # Получаем название таблицы из модели
        table_name = getattr(self.model, '__tablename__', None)

        # Проверяем глобальные права (старая система)
        self.can_edit = "can_edit" in permissions
        self.can_create = "can_create" in permissions
        self.can_delete = "can_delete" in permissions
        self.can_export = "can_export" in permissions
        self.can_view_details = "can_view_details" in permissions

        # Проверяем гранулированные права для конкретной таблицы
        if table_name:
            # Если есть специфичные права для таблицы, они имеют приоритет
            if f"{table_name}:edit" in permissions:
                self.can_edit = True
            elif f"{table_name}:edit" in [p for p in permissions if p.startswith(f"{table_name}:")]:
                # Если есть любые права для этой таблицы, но нет права на редактирование
                pass  # Оставляем значение из глобальных прав

            if f"{table_name}:create" in permissions:
                self.can_create = True

            if f"{table_name}:delete" in permissions:
                self.can_delete = True

            if f"{table_name}:export" in permissions:
                self.can_export = True

            if f"{table_name}:view" in permissions:
                self.can_view_details = True

    def has_table_access(self, permissions):
        """
        Проверяет, есть ли у пользователя доступ к таблице вообще
        :param permissions: список прав пользователя
        :return: True если есть доступ к таблице
        """
        table_name = getattr(self.model, '__tablename__', None)

        if not table_name:
            return True  # Если нет названия таблицы, разрешаем доступ

        # Проверяем глобальные права (старая система)
        if any(perm in permissions for perm in ["can_edit", "can_create", "can_delete", "can_export", "can_view_details"]):
            return True

        # Проверяем гранулированные права для конкретной таблицы
        table_permissions = [
            p for p in permissions if p.startswith(f"{table_name}:")]
        if table_permissions:
            # Если есть любые права для этой таблицы, значит есть доступ
            return True

        return False

    def is_accessible(self, request: Request) -> bool:
        """
        Проверка доступа к странице
        :param request:
        :return:
        """
        from db.models import User

        user_role = User.get_role(username=request.session.get("username", ""))
        has_role_permission = user_role in self.required_roles

        user_permissions = User.get_user_permissions(
            username=request.session.get("username", "")
        )
        self.apply_permissions(user_permissions)

        # Проверяем как права на роли, так и права на таблицу
        has_table_access = self.has_table_access(user_permissions)

        return has_role_permission and has_table_access

    def is_visible(self, request: Request) -> bool:
        """
        Проверка видимости в меню
        :param request:
        :return:
        """
        from db.models import User
        username = request.session.get("username", None)

        user_role = User.get_role(username=request.session.get("username", ""))
        has_role_permission = user_role in self.required_roles

        user_permissions = User.get_user_permissions(
            username=request.session.get("username", "")
        )
        self.apply_permissions(user_permissions)
        if not self.can_view_details:
            # Если нет прав на просмотр деталей, то не показываем в меню
            return
        return self.can_view_details

    def sort_query(self, stmt, request: Request):
        """
        Сортировка результатов таблицы
        :param stmt:
        :param request:
        :return:
        """
        sort_by = request.query_params.get("sortBy", None)

        if sort_by and sort_by in self.filter_fields:
            sort_by += f".{self.filter_fields[sort_by]}"

        sort = request.query_params.get("sort", "asc")

        if sort_by:
            sort_fields = [(sort_by, sort == "desc")]
        else:
            sort_fields = self._get_default_sort()

        for sort_field, is_desc in sort_fields:
            model = self.model
            parts = sort_field.split(".")
            for part in parts[:-1]:
                model = getattr(model, part).mapper.class_
                stmt = stmt.join(model)

            # Сортировка по дате без учета года (по дню и месяцу)
            # Если сортировка идет по полю 'birthday' или 'employment_date', то сортировка происходит по месяцу и дню
            if parts[-1] == "birthday" or parts[-1] == "employment_date":
                if is_desc:
                    stmt = stmt.order_by(
                        desc(extract("month", getattr(model, parts[-1]))),
                        desc(extract("day", getattr(model, parts[-1]))),
                    )
                else:
                    stmt = stmt.order_by(
                        asc(extract("month", getattr(model, parts[-1]))),
                        asc(extract("day", getattr(model, parts[-1]))),
                    )
            else:
                # Для других полей выполняется обычная сортировка
                if is_desc:
                    stmt = stmt.order_by(desc(getattr(model, parts[-1])))
                else:
                    stmt = stmt.order_by(asc(getattr(model, parts[-1])))

        return stmt

    def search_query(self, stmt, term: str):
        expressions = []
        joined_tables = {}

        print(f"Search term: {term}")

        if ':' in term:
            field_name, search_value = term.split(":", 1)
        else:
            field_name = None
            search_value = term

        if "to" in search_value:
            try:
                start_date_str, end_date_str = search_value.split(" to ")

                # Ожидаемый формат: день.месяц
                date_format = "%d.%m"
                start_date = datetime.strptime(
                    start_date_str.strip(), date_format)
                end_date = datetime.strptime(end_date_str.strip(), date_format)

                field = getattr(self.model, field_name)

                if isinstance(field.type, (Date, DateTime)):
                    if start_date.month == end_date.month:
                        # Один и тот же месяц
                        expressions.append(
                            and_(
                                func.extract(
                                    "month", field) == start_date.month,
                                func.extract("day", field) >= start_date.day,
                                func.extract("day", field) <= end_date.day
                            )
                        )
                    else:
                        # Разные месяцы
                        expressions.append(
                            or_(
                                and_(
                                    func.extract(
                                        "month", field) > start_date.month,
                                    func.extract(
                                        "month", field) < end_date.month
                                ),
                                and_(
                                    func.extract(
                                        "month", field) == start_date.month,
                                    func.extract(
                                        "day", field) >= start_date.day
                                ),
                                and_(
                                    func.extract(
                                        "month", field) == end_date.month,
                                    func.extract("day", field) <= end_date.day
                                )
                            )
                        )
                else:
                    print(f"Поле {field_name} не является датой.")
                    return stmt

            except ValueError as e:
                print(f"Ошибка преобразования дат: {e}")
                print("Убедитесь, что даты в формате dd.mm.")
                return stmt

        else:
            try:
                # Сравниваем одну дату, без учета года
                date_format = "%d.%m"
                single_date = datetime.strptime(
                    search_value.strip(), date_format)

                field = getattr(self.model, field_name)

                if isinstance(field.type, (Date, DateTime)):
                    expressions.append(
                        and_(
                            func.extract("day", field) == single_date.day,
                            func.extract("month", field) == single_date.month
                        )
                    )
                else:
                    print(f"Поле {field_name} не является датой.")
                    return stmt

            except ValueError:
                for field in self._search_fields:
                    if field_name and field_name != field:
                        continue

                    if field in self.filter_fields:
                        field += f".{self.filter_fields[field]}"

                    parts = field.split(".")
                    model = self.model

                    for part in parts[:-1]:
                        if part not in joined_tables:
                            relation = getattr(model, part)
                            model = relation.mapper.class_
                            alias = aliased(model)
                            stmt = stmt.join(alias, relation)
                            joined_tables[part] = alias
                        else:
                            model = joined_tables[part]

                    field = getattr(model, parts[-1])
                    expressions.append(
                        cast(field, String).ilike(f"%{search_value}%")
                    )

        if expressions:
            stmt = stmt.filter(and_(*expressions))
        return stmt

    @action(
        name="view_change_history",
        label="Просмотр истории изменений",
        add_in_detail=True,
        add_in_list=True,
    )
    async def view_change_history(self, request: Request):
        """
        Действие для просмотра истории изменений выбранных записей
        """
        # Получаем ID выбранных записей
        pks = request.query_params.get("pks", "").split(",")

        # Очищаем пустые значения
        pks = [pk.strip() for pk in pks if pk.strip()]

        print(f"DEBUG: pks = {pks}")
        print(f"DEBUG: request.url = {request.url}")
        print(f"DEBUG: request.base_url = {request.base_url}")

        if not pks:
            # Если не выбраны записи, перенаправляем обратно
            return RedirectResponse(
                request.headers.get("Referer") or
                request.url_for("admin:list", identity=self.identity)
            )

        # Получаем название таблицы из модели
        table_name = getattr(self.model, '__tablename__', None)

        print(f"DEBUG: table_name = {table_name}")

        if not table_name:
            # Если нет названия таблицы, перенаправляем обратно
            return RedirectResponse(
                request.headers.get("Referer") or
                request.url_for("admin:list", identity=self.identity)
            )

        # Формируем URL для перехода к нашей специальной странице
        # Используем абсолютный URL
        base_url = str(request.base_url).rstrip('/') + "/change-history"

        print(f"DEBUG: base_url = {base_url}")

        # Создаем параметры фильтрации
        filter_params = []
        filter_params.append(f"table_name={table_name}")

        # Добавляем фильтр по ID записей
        for pk in pks:
            filter_params.append(f"record_id={pk}")

        # Формируем финальный URL с параметрами
        if filter_params:
            filtered_url = f"{base_url}?{'&'.join(filter_params)}"
        else:
            filtered_url = base_url

        print(f"DEBUG: filtered_url = {filtered_url}")

        return RedirectResponse(filtered_url)
