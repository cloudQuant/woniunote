"""
数据库模型
"""
from app.models.user import User
from app.models.article import Article
from app.models.comment import Comment
from app.models.favorite import Favorite
from app.models.credit import Credit
from app.models.comment_vote import CommentVote
from app.models.math_training import MathTrainingRecord, MathTrainingWrongAnswer

__all__ = [
    "User", "Article", "Comment", "Favorite", "Credit",
    "CommentVote", "MathTrainingRecord", "MathTrainingWrongAnswer"
]
