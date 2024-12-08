from sqlalchemy import Column, Integer, String, REAL, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

import datetime
from database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    ipn = Column(Integer, unique=True)
    full_name = Column(String(150))
    contacts = Column(String(150))
    photo = Column(String(150))
    passport = Column(String(100))
    email = Column(String(120), nullable=True)
    role = Column(String(50), nullable=False, default='taker')

    favorites = relationship('Favorite', back_populates='user')

    def __repr__(self):
        return f'<User {self.login}, {self.full_name}>'


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    photo = Column(String(150))
    name = Column(String(50), unique=False)
    description = Column(String(250))
    price_hour = Column(REAL)
    price_day = Column(REAL)
    price_week = Column(REAL)
    price_month = Column(REAL)
    owner_id = Column(Integer, ForeignKey('users.id'))

    favorites = relationship('Favorite', back_populates='item')

    def __repr__(self):
        return f'<Item {self.name}, {self.id}, Owner: {self.owner_id}>'


class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text)
    start_date = Column(String)
    end_date = Column(String)
    status = Column(String, default='pending')
    leaser_id = Column(Integer, ForeignKey('users.id'))
    taker_id = Column(Integer, ForeignKey('users.id'))
    item_id = Column(Integer, ForeignKey('items.id'))

    leaser = relationship('User', foreign_keys=[leaser_id])
    taker = relationship('User', foreign_keys=[taker_id])
    item = relationship('Item', backref='contracts')

    def __repr__(self):
        return f'<Contract {self.id}, Leaser: {self.leaser_id}, Taker: {self.taker_id}>'

class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)

    user = relationship('User', back_populates='favorites')
    item = relationship('Item', back_populates='favorites')

    def __repr__(self):
        return f'<Favorite {self.id}, User: {self.user_id}, Item: {self.item_id}>'

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey('users.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    text = Column(Text)
    grade = Column(Integer)
    contract_id = Column(Integer, ForeignKey('contracts.id'))


    def __repr__(self):
        return f'<Feedback {self.id}, Author: {self.author_id}, User: {self.user_id}, Grade: {self.grade}>'

class SearchHistory(Base):
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    search_text = Column(Text)
    timestamp = Column(Integer)

    def __repr__(self):
        return f'<SearchHistory {self.id}, User: {self.user_id}, Search: {self.search_text}>'

class Leaser(Base):
    __tablename__ = 'leasers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150))

    def __repr__(self):
        return f'<Leaser {self.name}>'
