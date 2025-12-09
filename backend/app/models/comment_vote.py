"""
评论投票模型模块

用于记录用户对评论的点赞/踩操作。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class CommentVote(Base):
    """
    评论投票表
    
    记录用户对评论的评价（点赞或踩）。
    
    Attributes:
        id (int): 投票 ID，主键
        userid (int): 用户 ID，外键关联 users 表
        commentid (int): 评论 ID，外键关联 comment 表
        vote_type (int): 投票类型 (1: 点赞, -1: 踩)
        createtime (datetime): 创建时间
    """
    __tablename__ = "comment_vote"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    # 关联到 comment 表的 commentid 字段（注意表名是 comment，而不是 comments）
    commentid = Column(Integer, ForeignKey("comment.commentid"), nullable=False, index=True)
    vote_type = Column(Integer, nullable=False)  # 1: 点赞, -1: 踩
    createtime = Column(DateTime, default=datetime.now)
    
    # 唯一约束：每个用户对每条评论只能投一次票
    __table_args__ = (
        UniqueConstraint('userid', 'commentid', name='uix_user_comment_vote'),
    )
    
    # 关系
    user = relationship("User", backref="comment_votes")
    comment = relationship("Comment", backref="votes")
    
    def __repr__(self):
        return f"<CommentVote user={self.userid} comment={self.commentid} type={self.vote_type}>"
