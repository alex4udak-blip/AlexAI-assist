"""Cross-database compatible SQLAlchemy types.

These TypeDecorators enable models to work with both PostgreSQL (production)
and SQLite (testing) by using native types where available and JSON fallback.
"""

import json
import uuid
from typing import Any

from sqlalchemy import Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine


class PortableUUID(TypeDecorator[uuid.UUID]):
    """UUID type that works with PostgreSQL and SQLite.

    - PostgreSQL: Uses native UUID type
    - SQLite: Stores as 36-char string
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: uuid.UUID | str | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        # SQLite: store as string
        return str(value) if isinstance(value, uuid.UUID) else value

    def process_result_value(self, value: str | uuid.UUID | None, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSONType(TypeDecorator[dict[str, Any]]):
    """JSON type that works with PostgreSQL JSONB and SQLite TEXT.

    - PostgreSQL: Uses native JSONB with indexing support
    - SQLite: Stores as JSON text string
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: serialize to JSON string
        return json.dumps(value, default=str)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: parse JSON string
        if isinstance(value, str):
            return json.loads(value)
        return value


class StringArray(TypeDecorator[list[str]]):
    """Array of strings that works with PostgreSQL ARRAY and SQLite TEXT.

    - PostgreSQL: Uses native ARRAY(String) type
    - SQLite: Stores as JSON array string
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            from sqlalchemy import String

            return dialect.type_descriptor(postgresql.ARRAY(String))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[str] | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: serialize to JSON string
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> list[str] | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: parse JSON string
        if isinstance(value, str):
            return json.loads(value)
        return value


class UUIDArray(TypeDecorator[list[uuid.UUID]]):
    """Array of UUIDs that works with PostgreSQL ARRAY(UUID) and SQLite TEXT.

    - PostgreSQL: Uses native ARRAY(UUID) type
    - SQLite: Stores as JSON array of UUID strings
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.ARRAY(postgresql.UUID(as_uuid=True)))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[uuid.UUID] | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: serialize to JSON array of strings
        return json.dumps([str(v) for v in value])

    def process_result_value(self, value: Any, dialect: Dialect) -> list[uuid.UUID] | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # SQLite: parse JSON and convert to UUIDs
        if isinstance(value, str):
            return [uuid.UUID(v) for v in json.loads(value)]
        return value
