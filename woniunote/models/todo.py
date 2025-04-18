#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Todo模型定义
"""
from woniunote.common.database import db

# Todo模型定义
class Item(db.Model):
    __tablename__ = "todo_item"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    body = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('todo_category.id'))
    category = db.relationship('Category', backref=db.backref('items', lazy='dynamic'))


class Category(db.Model):
    __tablename__ = "todo_category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
