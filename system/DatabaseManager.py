# -*- coding: utf-8 -*-
# ! python3

# Developed by: Aleksandr Kireev
# Created: 01.11.2023
# Updated: 20.11.2024
# Website: https://bespredel.name

import json
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr, sessionmaker
from config import config
from system.Logger import Logger


class TablePrefixBase:
    __table_prefix__ = config.get('db.prefix', '')

    @declared_attr
    def __tablename__(cls):
        return cls.__table_prefix__ + cls.__name__.lower()


# Defining the base class
Base = declarative_base(cls=TablePrefixBase)


class CVCounter(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean, default=True)
    location = Column(String(255), nullable=False)
    total_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    defects_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    parts = Column(Text, nullable=True)
    custom_fields = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DatabaseManager:
    """
    Database manager using SQLAlchemy.

    Args:
        uri (str): Database connection URL.
        prefix (str, optional): Table prefix. Defaults to ''.
    """

    def __init__(self, uri, prefix=''):
        self.__logger = Logger()
        self.__engine = create_engine(uri)
        self.__prefix = prefix
        self.__sessionmaker = sessionmaker(bind=self.__engine)

        # Create tables if they don't exist yet
        Base.metadata.create_all(self.__engine)

    """
    Creates and returns a new session.
    
    Returns:
        Session: A new session.
    """

    def create_session(self):
        return self.__sessionmaker()

    """
    Saves a result to the database.
    
    Args:
        location (str): The location of the result.
        total_count (int, optional): The total count. Defaults to 0.
        source_count (int, optional): The source count. Defaults to 0.
        defects_count (int, optional): The defects count. Defaults to 0.
        correct_count (int, optional): The correct count. Defaults to 0.
        custom_fields (str, optional): The custom fields. Defaults to ''.
        active (bool, optional): The active status. Defaults to True.
    """

    def save_result(self, location, total_count=0, source_count=0, defects_count=0, correct_count=0, custom_fields='', active=True):
        session = self.create_session()
        try:
            result = session.query(CVCounter).filter_by(location=location, active=True).first()

            new_custom_fields = {}
            if custom_fields:
                new_custom_fields = json.loads(custom_fields if custom_fields else '{}')

            if result:
                # Обновляем существующие custom_fields
                existing_custom_fields = json.loads(result.custom_fields if result.custom_fields else '{}')
                if new_custom_fields:
                    # Объединение нового и существующего словаря
                    existing_custom_fields.update(new_custom_fields)
                    custom_fields = json.dumps(existing_custom_fields)

            if result:
                # Обновляем существующую запись
                result.active = active
                result.total_count = total_count
                result.source_count = source_count
                result.defects_count = defects_count
                result.correct_count = correct_count
                result.custom_fields = custom_fields
                result.updated_at = datetime.now()
            else:
                # Вставляем новую запись
                new_result = CVCounter(
                    active=active,
                    location=location,
                    total_count=total_count,
                    source_count=source_count,
                    defects_count=defects_count,
                    correct_count=correct_count,
                    custom_fields=custom_fields,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(new_result)
            session.commit()
            return True
        except SQLAlchemyError as error:
            session.rollback()
            self.__logger.error(str(error))
            self.__logger.log_exception()
            return False
        finally:
            session.close()

    """
    Saves a part result to the database.
    
    Args:
        location (str): The location of the result.
        current_count (int, optional): The current count. Defaults to 0.
        total_count (int, optional): The total count. Defaults to 0.
        defects_count (int, optional): The defects count. Defaults to 0.
        correct_count (int, optional): The correct count. Defaults to 0.
    """

    def save_part_result(self, location, current_count=0, total_count=0, defects_count=0, correct_count=0):
        session = self.create_session()
        try:
            result = session.query(CVCounter).filter_by(location=location, active=True).first()
            if result:
                # Обновляем поле parts
                parts = json.loads(result.parts) if result.parts else []
                parts.append({
                    'current': current_count,
                    'total': total_count,
                    'defects': defects_count,
                    'correct': correct_count,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                parts = sorted(parts, key=lambda x: x['created_at'], reverse=True)
                result.parts = json.dumps(parts)
                result.updated_at = datetime.now()
                session.commit()
                return True
            return False
        except SQLAlchemyError as error:
            session.rollback()
            self.__logger.error(str(error))
            self.__logger.log_exception()
            return False
        finally:
            session.close()

    """
    Closes the current counter for the specified location.
    
    Args:
        location (str): The location of the counter to close.
    """

    def close_current_count(self, location):
        session = self.create_session()
        try:
            result = session.query(CVCounter).filter_by(location=location, active=True).first()
            if result:
                result.active = False
                result.updated_at = datetime.now()
                session.commit()
                return True
            return False
        except SQLAlchemyError as error:
            session.rollback()
            self.__logger.error(str(error))
            return False
        finally:
            session.close()

    """
    Returns the current counter for the given key.

    Args:
        key (str, optional): The key. Defaults to ''.

    Returns:
        CVCounter: The current counter.
    """

    def get_current_count(self, key=''):
        session = self.create_session()
        try:
            result = session.query(CVCounter).filter_by(active=True, location=key).first()
            return result if result else None
        except SQLAlchemyError as error:
            self.__logger.error(str(error))
            return None
        finally:
            session.close()

    """
    Returns the count for the given id.

    Args:
        rec_id (int): The record id.

    Returns:
        CVCounter: The count.
    """

    def get_count(self, rec_id):
        session = self.create_session()
        try:
            result = session.query(CVCounter).filter_by(id=rec_id).first()
            return result if result else None
        except SQLAlchemyError as error:
            self.__logger.error(str(error))
            return None
        finally:
            session.close()

    """
    Returns all counters for the given key.

    Args:
        key (str, optional): The key. Defaults to ''.

    Returns:
        list: A list of counters.
    """

    def get_paginated(self, key: str = '', page: int = 1, per_page: int = 10):
        session = self.create_session()
        try:
            query = session.query(CVCounter).filter_by(location=key)
            total = query.count()  # Getting the total number of records
            results = query.offset((page - 1) * per_page).limit(per_page).all()  # Applying offset and limit

            return {
                'total': total,
                'page': page,
                'per_page': per_page,
                'results': results,
                'has_next': page * per_page < total,  # Checking if there is a next page
                'has_prev': page > 1  # Checking if there is a previous page
            }
        except SQLAlchemyError as error:
            self.__logger.error(f"Error retrieving counters for key '{key}': {str(error)}")
            return None  # Return None on error
        finally:
            session.close()
