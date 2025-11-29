"""
评论模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Comment(Base):
    """评论表"""
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
