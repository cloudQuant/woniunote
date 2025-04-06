#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Card模型定义
"""
from woniunote.common.database import db

# Card模型定义
class Card(db.Model):
    __tablename__ = "card"
    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    type = db.Column(db.Integer, default=1)
    headline = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, default="")
    createtime = db.Column(db.DateTime)
    updatetime = db.Column(db.DateTime)
    donetime = db.Column(db.DateTime)
    usedtime = db.Column(db.Integer, default=0)
    begintime = db.Column(db.DateTime)
    endtime = db.Column(db.DateTime)
    cardcategory_id = db.Column(db.Integer, db.ForeignKey('cardcategory.id'), default=1)
    cardcategory = db.relationship('CardCategory', backref=db.backref('cards', lazy='dynamic'))


class CardCategory(db.Model):
    __tablename__ = "cardcategory"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
