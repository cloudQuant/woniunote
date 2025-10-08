from flask import Flask
from sqlalchemy import Index
from woniunote.common.database import db, SQLALCHEMY_DATABASE_URI
from woniunote.common.create_database import Article, Comment, Favorite

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def create_indexes():
    app = create_app()
    with app.app_context():
        engine = db.engine
        idxs = [
            Index('ix_article_checked', Article.__table__.c.checked),
            Index('ix_article_drafted', Article.__table__.c.drafted),
            Index('ix_article_checked_drafted_createtime', Article.__table__.c.checked, Article.__table__.c.drafted, Article.__table__.c.createtime),
            Index('ix_article_createtime', Article.__table__.c.createtime),
            Index('ix_article_readcount', Article.__table__.c.readcount),
            Index('ix_article_type', Article.__table__.c.type),
            Index('ix_article_recommended', Article.__table__.c.recommended),
            Index('ix_comment_articleid', Comment.__table__.c.articleid),
            Index('ix_comment_userid', Comment.__table__.c.userid),
            Index('ix_favorite_articleid', Favorite.__table__.c.articleid),
            Index('ix_favorite_userid', Favorite.__table__.c.userid),
        ]
        for idx in idxs:
            idx.create(bind=engine, checkfirst=True)

if __name__ == '__main__':
    create_indexes()
