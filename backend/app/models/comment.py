"""
评论模型模块

本模块定义了评论相关的数据模型。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Comment(Base):
    """
    评论表
    
    存储用户对文章的评论信息。
    
    Attributes:
        commentid (int): 评论 ID，主键
        userid (int): 用户 ID，外键关联 users 表
        articleid (int): 文章 ID，外键关联 article 表
        content (str): 评论内容
        ipaddr (str): 评论者 IP 地址
        replyid (int): 回复的评论 ID (如果是回复)
        agreecount (int): 点赞数
        opposecount (int): 反对数
        hidden (int): 是否隐藏 (0: 否, 1: 是)
        createtime (datetime): 创建时间
        updatetime (datetime): 更新时间
    """
    __tablename__ = "comment"
    
    commentid = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    articleid = Column(Integer, ForeignKey("article.articleid"), nullable=False, index=True)
    content = Column(Text(65536), nullable=False)
    ipaddr = Column(String(30))
    replyid = Column(Integer)
    agreecount = Column(Integer, default=0)
    opposecount = Column(Integer, default=0)
    hidden = Column(Integer, default=0)
    createtime = Column(DateTime, default=datetime.now)
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="comments")
    article = relationship("Article", back_populates="comments")
    
    def __repr__(self):
        return f"<Comment {self.commentid}>"
