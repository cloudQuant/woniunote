#!/usr/bin/env python3
"""
Phase 5 用户体验优化模块
提供个性化推荐、智能搜索、实时通知、用户行为分析等用户体验增强功能
"""

import os
import time
import json
import logging
import hashlib
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from functools import wraps
from enum import Enum
import re
import math
from flask import session, request, g, current_app
from flask_socketio import SocketIO, emit
import warnings
# Suppress jieba pkg_resources deprecation warning
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
    import jieba
    import jieba.analyse

logger = logging.getLogger(__name__)

class UserActionType(Enum):
    """用户行为类型枚举"""
    VIEW = "view"
    CLICK = "click"
    SEARCH = "search"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LIKE = "like"
    SHARE = "share"
    COMMENT = "comment"
    BOOKMARK = "bookmark"

class NotificationType(Enum):
    """通知类型枚举"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"
    REMINDER = "reminder"

@dataclass
class UserAction:
    """用户行为记录"""
    user_id: str
    action_type: UserActionType
    timestamp: datetime
    target_type: str  # 目标类型：article, comment, user等
    target_id: str
    metadata: Dict[str, Any]
    session_id: str
    ip_address: str
    user_agent: str

@dataclass
class UserPreference:
    """用户偏好"""
    user_id: str
    category_weights: Dict[str, float]  # 分类权重
    tag_weights: Dict[str, float]      # 标签权重
    author_weights: Dict[str, float]   # 作者权重
    time_preference: Dict[str, float]  # 时间偏好
    content_length_preference: float   # 内容长度偏好
    interaction_patterns: Dict[str, float]  # 交互模式

@dataclass
class Notification:
    """通知消息"""
    id: str
    user_id: str
    notification_type: NotificationType
    title: str
    content: str
    created_at: datetime
    read_at: Optional[datetime]
    action_url: Optional[str]
    metadata: Dict[str, Any]

class UserBehaviorAnalyzer:
    """用户行为分析器"""
    
    def __init__(self):
        self.user_actions = defaultdict(list)  # 用户行为记录
        self.session_data = defaultdict(dict)   # 会话数据
        self.user_preferences = {}              # 用户偏好
        self.lock = threading.RLock()
        
        # 分析参数
        self.preference_decay = 0.95  # 偏好衰减因子
        self.min_actions_for_preference = 10  # 建立偏好的最少行为数
        
    def record_action(self, action: UserAction):
        """记录用户行为"""
        with self.lock:
            self.user_actions[action.user_id].append(action)
            
            # 保持最近1000个行为记录
            if len(self.user_actions[action.user_id]) > 1000:
                self.user_actions[action.user_id].pop(0)
            
            # 更新会话数据
            self._update_session_data(action)
            
            # 异步更新用户偏好
            self._update_user_preferences(action.user_id)
    
    def _update_session_data(self, action: UserAction):
        """更新会话数据"""
        session_key = action.session_id
        
        if session_key not in self.session_data:
            self.session_data[session_key] = {
                'start_time': action.timestamp,
                'last_activity': action.timestamp,
                'page_views': 0,
                'actions_count': 0,
                'unique_targets': set()
            }
        
        session = self.session_data[session_key]
        session['last_activity'] = action.timestamp
        session['actions_count'] += 1
        session['unique_targets'].add(f"{action.target_type}:{action.target_id}")
        
        if action.action_type == UserActionType.VIEW:
            session['page_views'] += 1
    
    def _update_user_preferences(self, user_id: str):
        """更新用户偏好"""
        try:
            actions = self.user_actions[user_id]
            
            if len(actions) < self.min_actions_for_preference:
                return
            
            # 初始化偏好
            if user_id not in self.user_preferences:
                self.user_preferences[user_id] = UserPreference(
                    user_id=user_id,
                    category_weights={},
                    tag_weights={},
                    author_weights={},
                    time_preference={},
                    content_length_preference=0.5,
                    interaction_patterns={}
                )
            
            preference = self.user_preferences[user_id]
            
            # 分析最近行为
            recent_actions = actions[-100:]  # 最近100个行为
            
            # 分析分类偏好
            self._analyze_category_preferences(recent_actions, preference)
            
            # 分析标签偏好
            self._analyze_tag_preferences(recent_actions, preference)
            
            # 分析作者偏好
            self._analyze_author_preferences(recent_actions, preference)
            
            # 分析时间偏好
            self._analyze_time_preferences(recent_actions, preference)
            
            # 分析交互模式
            self._analyze_interaction_patterns(recent_actions, preference)
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
    
    def _analyze_category_preferences(self, actions: List[UserAction], preference: UserPreference):
        """分析分类偏好"""
        category_scores = defaultdict(float)
        
        for action in actions:
            category = action.metadata.get('category', 'unknown')
            
            # 不同行为的权重
            weight = {
                UserActionType.VIEW: 1.0,
                UserActionType.LIKE: 3.0,
                UserActionType.SHARE: 2.5,
                UserActionType.COMMENT: 2.0,
                UserActionType.BOOKMARK: 4.0
            }.get(action.action_type, 1.0)
            
            # 时间衰减
            age_days = (datetime.now() - action.timestamp).days
            time_weight = math.exp(-age_days * 0.1)  # 指数衰减
            
            category_scores[category] += weight * time_weight
        
        # 归一化
        total_score = sum(category_scores.values())
        if total_score > 0:
            for category, score in category_scores.items():
                preference.category_weights[category] = score / total_score
    
    def _analyze_tag_preferences(self, actions: List[UserAction], preference: UserPreference):
        """分析标签偏好"""
        tag_scores = defaultdict(float)
        
        for action in actions:
            tags = action.metadata.get('tags', [])
            
            weight = {
                UserActionType.VIEW: 0.5,
                UserActionType.LIKE: 2.0,
                UserActionType.SHARE: 1.5,
                UserActionType.COMMENT: 1.0,
                UserActionType.BOOKMARK: 3.0
            }.get(action.action_type, 0.5)
            
            age_days = (datetime.now() - action.timestamp).days
            time_weight = math.exp(-age_days * 0.1)
            
            for tag in tags:
                tag_scores[tag] += weight * time_weight
        
        # 归一化
        total_score = sum(tag_scores.values())
        if total_score > 0:
            for tag, score in tag_scores.items():
                preference.tag_weights[tag] = score / total_score
    
    def _analyze_author_preferences(self, actions: List[UserAction], preference: UserPreference):
        """分析作者偏好"""
        author_scores = defaultdict(float)
        
        for action in actions:
            author = action.metadata.get('author_id')
            if not author:
                continue
            
            weight = {
                UserActionType.VIEW: 0.5,
                UserActionType.LIKE: 2.0,
                UserActionType.SHARE: 1.5,
                UserActionType.COMMENT: 1.0,
                UserActionType.BOOKMARK: 2.5
            }.get(action.action_type, 0.5)
            
            age_days = (datetime.now() - action.timestamp).days
            time_weight = math.exp(-age_days * 0.1)
            
            author_scores[author] += weight * time_weight
        
        # 归一化
        total_score = sum(author_scores.values())
        if total_score > 0:
            for author, score in author_scores.items():
                preference.author_weights[author] = score / total_score
    
    def _analyze_time_preferences(self, actions: List[UserAction], preference: UserPreference):
        """分析时间偏好"""
        hour_scores = defaultdict(float)
        
        for action in actions:
            hour = action.timestamp.hour
            hour_scores[str(hour)] += 1
        
        # 归一化
        total_count = sum(hour_scores.values())
        if total_count > 0:
            for hour, count in hour_scores.items():
                preference.time_preference[hour] = count / total_count
    
    def _analyze_interaction_patterns(self, actions: List[UserAction], preference: UserPreference):
        """分析交互模式"""
        patterns = defaultdict(int)
        
        # 行为序列分析
        for i in range(len(actions) - 1):
            current_action = actions[i].action_type.value
            next_action = actions[i + 1].action_type.value
            pattern = f"{current_action}->{next_action}"
            patterns[pattern] += 1
        
        # 归一化
        total_patterns = sum(patterns.values())
        if total_patterns > 0:
            for pattern, count in patterns.items():
                preference.interaction_patterns[pattern] = count / total_patterns
    
    def get_user_preference(self, user_id: str) -> Optional[UserPreference]:
        """获取用户偏好"""
        with self.lock:
            return self.user_preferences.get(user_id)
    
    def get_user_activity_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """获取用户活动摘要"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=days)
            recent_actions = [
                action for action in self.user_actions[user_id]
                if action.timestamp >= cutoff_time
            ]
            
            if not recent_actions:
                return {}
            
            # 统计各类行为
            action_counts = defaultdict(int)
            target_types = defaultdict(int)
            daily_activity = defaultdict(int)
            
            for action in recent_actions:
                action_counts[action.action_type.value] += 1
                target_types[action.target_type] += 1
                day_key = action.timestamp.strftime('%Y-%m-%d')
                daily_activity[day_key] += 1
            
            return {
                'total_actions': len(recent_actions),
                'action_counts': dict(action_counts),
                'target_types': dict(target_types),
                'daily_activity': dict(daily_activity),
                'avg_daily_actions': len(recent_actions) / days,
                'active_days': len(daily_activity)
            }

class PersonalizedRecommendationEngine:
    """个性化推荐引擎"""
    
    def __init__(self, behavior_analyzer: UserBehaviorAnalyzer):
        self.behavior_analyzer = behavior_analyzer
        self.content_cache = {}  # 内容缓存
        self.similarity_cache = {}  # 相似度缓存
        self.lock = threading.RLock()
        
    def recommend_content(self, user_id: str, content_type: str = 'article', 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """推荐内容"""
        try:
            user_preference = self.behavior_analyzer.get_user_preference(user_id)
            
            if not user_preference:
                # 新用户，返回热门内容
                return self._get_popular_content(content_type, limit)
            
            # 获取候选内容
            candidates = self._get_candidate_content(content_type, user_id)
            
            # 计算推荐分数
            scored_candidates = []
            for candidate in candidates:
                score = self._calculate_recommendation_score(candidate, user_preference, user_id)
                scored_candidates.append((candidate, score))
            
            # 排序并返回top-k
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
            return [candidate for candidate, score in scored_candidates[:limit]]
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._get_popular_content(content_type, limit)
    
    def _get_candidate_content(self, content_type: str, user_id: str) -> List[Dict[str, Any]]:
        """获取候选内容"""
        # 这里需要根据实际的数据模型来实现
        # 示例返回空列表，实际应该从数据库获取
        return []
    
    def _calculate_recommendation_score(self, content: Dict[str, Any], 
                                      preference: UserPreference, user_id: str) -> float:
        """计算推荐分数"""
        score = 0.0
        
        # 分类匹配分数
        content_category = content.get('category', '')
        if content_category in preference.category_weights:
            score += preference.category_weights[content_category] * 0.3
        
        # 标签匹配分数
        content_tags = content.get('tags', [])
        tag_score = 0.0
        for tag in content_tags:
            if tag in preference.tag_weights:
                tag_score += preference.tag_weights[tag]
        score += (tag_score / max(len(content_tags), 1)) * 0.2
        
        # 作者偏好分数
        content_author = content.get('author_id', '')
        if content_author in preference.author_weights:
            score += preference.author_weights[content_author] * 0.2
        
        # 内容新鲜度分数
        content_date = content.get('created_at')
        if content_date:
            age_days = (datetime.now() - content_date).days
            freshness_score = math.exp(-age_days * 0.05)  # 指数衰减
            score += freshness_score * 0.1
        
        # 热度分数
        popularity = content.get('view_count', 0) + content.get('like_count', 0) * 2
        popularity_score = math.log(popularity + 1) / 10  # 对数缩放
        score += popularity_score * 0.1
        
        # 相似度分数（协同过滤）
        similarity_score = self._calculate_collaborative_filtering_score(content, user_id)
        score += similarity_score * 0.1
        
        return score
    
    def _calculate_collaborative_filtering_score(self, content: Dict[str, Any], user_id: str) -> float:
        """计算协同过滤分数"""
        try:
            # 简化的协同过滤实现
            content_id = content.get('id', '')
            
            # 找到与当前用户相似的用户
            similar_users = self._find_similar_users(user_id)
            
            # 计算这些用户对该内容的平均评分
            scores = []
            for similar_user_id, similarity in similar_users:
                user_actions = self.behavior_analyzer.user_actions.get(similar_user_id, [])
                
                # 查找该用户对该内容的行为
                for action in user_actions:
                    if (action.target_type == content.get('type', '') and 
                        action.target_id == content_id):
                        
                        action_score = {
                            UserActionType.VIEW: 1.0,
                            UserActionType.LIKE: 5.0,
                            UserActionType.SHARE: 4.0,
                            UserActionType.COMMENT: 3.0,
                            UserActionType.BOOKMARK: 5.0
                        }.get(action.action_type, 1.0)
                        
                        scores.append(action_score * similarity)
            
            return sum(scores) / len(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating collaborative filtering score: {e}")
            return 0.0
    
    def _find_similar_users(self, user_id: str, limit: int = 10) -> List[Tuple[str, float]]:
        """找到相似用户"""
        try:
            current_preference = self.behavior_analyzer.get_user_preference(user_id)
            if not current_preference:
                return []
            
            similarities = []
            
            for other_user_id, other_preference in self.behavior_analyzer.user_preferences.items():
                if other_user_id == user_id:
                    continue
                
                similarity = self._calculate_user_similarity(current_preference, other_preference)
                similarities.append((other_user_id, similarity))
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []
    
    def _calculate_user_similarity(self, pref1: UserPreference, pref2: UserPreference) -> float:
        """计算用户相似度"""
        try:
            similarity = 0.0
            
            # 分类偏好相似度
            category_sim = self._calculate_dict_similarity(pref1.category_weights, pref2.category_weights)
            similarity += category_sim * 0.4
            
            # 标签偏好相似度
            tag_sim = self._calculate_dict_similarity(pref1.tag_weights, pref2.tag_weights)
            similarity += tag_sim * 0.3
            
            # 作者偏好相似度
            author_sim = self._calculate_dict_similarity(pref1.author_weights, pref2.author_weights)
            similarity += author_sim * 0.2
            
            # 交互模式相似度
            pattern_sim = self._calculate_dict_similarity(pref1.interaction_patterns, pref2.interaction_patterns)
            similarity += pattern_sim * 0.1
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating user similarity: {e}")
            return 0.0
    
    def _calculate_dict_similarity(self, dict1: Dict[str, float], dict2: Dict[str, float]) -> float:
        """计算字典相似度（余弦相似度）"""
        if not dict1 or not dict2:
            return 0.0
        
        # 获取所有键的并集
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        # 构建向量
        vec1 = [dict1.get(key, 0.0) for key in all_keys]
        vec2 = [dict2.get(key, 0.0) for key in all_keys]
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _get_popular_content(self, content_type: str, limit: int) -> List[Dict[str, Any]]:
        """获取热门内容"""
        # 这里需要根据实际的数据模型来实现
        # 示例返回空列表，实际应该从数据库获取热门内容
        return []

class SmartSearchEngine:
    """智能搜索引擎"""
    
    def __init__(self):
        self.search_history = defaultdict(list)  # 搜索历史
        self.search_index = {}  # 搜索索引
        self.keyword_suggestions = defaultdict(set)  # 关键词建议
        self.lock = threading.RLock()
        
        # 初始化jieba分词
        jieba.initialize()
    
    def search(self, query: str, user_id: str = None, content_type: str = 'all', 
              limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """智能搜索"""
        try:
            # 记录搜索历史
            if user_id:
                self._record_search(user_id, query)
            
            # 预处理查询
            processed_query = self._preprocess_query(query)
            
            # 执行搜索
            results = self._execute_search(processed_query, content_type, limit, offset)
            
            # 个性化排序
            if user_id:
                results = self._personalize_results(results, user_id)
            
            # 生成搜索建议
            suggestions = self._generate_suggestions(query, user_id)
            
            return {
                'query': query,
                'results': results,
                'total_count': len(results),
                'suggestions': suggestions,
                'query_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                'query': query,
                'results': [],
                'total_count': 0,
                'suggestions': [],
                'error': str(e)
            }
    
    def _record_search(self, user_id: str, query: str):
        """记录搜索历史"""
        with self.lock:
            search_record = {
                'query': query,
                'timestamp': datetime.now(),
                'results_count': 0  # 将在搜索完成后更新
            }
            
            self.search_history[user_id].append(search_record)
            
            # 保持最近100次搜索
            if len(self.search_history[user_id]) > 100:
                self.search_history[user_id].pop(0)
    
    def _preprocess_query(self, query: str) -> Dict[str, Any]:
        """预处理查询"""
        # 去除多余空格
        query = re.sub(r'\s+', ' ', query.strip())
        
        # 分词
        words = list(jieba.cut_for_search(query))
        
        # 提取关键词
        keywords = jieba.analyse.extract_tags(query, topK=10, withWeight=True)
        
        # 检测查询意图
        intent = self._detect_search_intent(query)
        
        return {
            'original_query': query,
            'words': words,
            'keywords': keywords,
            'intent': intent
        }
    
    def _detect_search_intent(self, query: str) -> str:
        """检测搜索意图"""
        query_lower = query.lower()
        
        # 时间相关
        time_keywords = ['今天', '昨天', '最近', '本周', '本月', '去年']
        if any(keyword in query for keyword in time_keywords):
            return 'time_based'
        
        # 用户相关
        user_keywords = ['作者', '用户', '的文章', '写的']
        if any(keyword in query for keyword in user_keywords):
            return 'user_based'
        
        # 类型相关
        type_keywords = ['教程', '笔记', '文档', '代码', '问答']
        if any(keyword in query for keyword in type_keywords):
            return 'type_based'
        
        return 'general'
    
    def _execute_search(self, processed_query: Dict[str, Any], content_type: str, 
                       limit: int, offset: int) -> List[Dict[str, Any]]:
        """执行搜索"""
        # 这里需要根据实际的数据模型来实现搜索逻辑
        # 示例返回空列表，实际应该在数据库中搜索
        return []
    
    def _personalize_results(self, results: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        """个性化搜索结果排序"""
        try:
            from .performance_enhanced import get_performance_manager
            behavior_analyzer = get_performance_manager().behavior_analyzer
            
            user_preference = behavior_analyzer.get_user_preference(user_id)
            if not user_preference:
                return results
            
            # 为每个结果计算个性化分数
            scored_results = []
            for result in results:
                base_score = result.get('score', 0.0)
                
                # 分类偏好加权
                category = result.get('category', '')
                category_weight = user_preference.category_weights.get(category, 0.1)
                
                # 作者偏好加权
                author_id = result.get('author_id', '')
                author_weight = user_preference.author_weights.get(author_id, 0.1)
                
                # 计算个性化分数
                personal_score = base_score * (1 + category_weight * 0.3 + author_weight * 0.2)
                
                result['personal_score'] = personal_score
                scored_results.append(result)
            
            # 按个性化分数排序
            scored_results.sort(key=lambda x: x['personal_score'], reverse=True)
            
            return scored_results
            
        except Exception as e:
            logger.error(f"Error personalizing search results: {e}")
            return results
    
    def _generate_suggestions(self, query: str, user_id: str = None) -> List[str]:
        """生成搜索建议"""
        suggestions = []
        
        try:
            # 基于历史搜索的建议
            if user_id and user_id in self.search_history:
                recent_searches = self.search_history[user_id][-10:]
                for search_record in recent_searches:
                    search_query = search_record['query']
                    if search_query.startswith(query) and search_query != query:
                        suggestions.append(search_query)
            
            # 基于热门搜索的建议
            popular_queries = self._get_popular_queries()
            for popular_query in popular_queries:
                if query.lower() in popular_query.lower() and popular_query not in suggestions:
                    suggestions.append(popular_query)
            
            # 基于关键词扩展的建议
            keyword_expansions = self._expand_keywords(query)
            suggestions.extend(keyword_expansions)
            
        except Exception as e:
            logger.error(f"Error generating search suggestions: {e}")
        
        return suggestions[:5]  # 返回最多5个建议
    
    def _get_popular_queries(self) -> List[str]:
        """获取热门搜索词"""
        # 统计所有用户的搜索词频
        query_counts = defaultdict(int)
        
        for user_searches in self.search_history.values():
            for search_record in user_searches:
                query_counts[search_record['query']] += 1
        
        # 按频率排序
        sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [query for query, count in sorted_queries[:20]]
    
    def _expand_keywords(self, query: str) -> List[str]:
        """扩展关键词"""
        # 简单的关键词扩展逻辑
        expansions = []
        
        # 同义词扩展（需要同义词词典）
        synonyms = {
            '教程': ['指南', '入门', '学习'],
            '问题': ['问答', '疑问', '困惑'],
            '代码': ['程序', '编程', '源码']
        }
        
        for word in jieba.cut(query):
            if word in synonyms:
                for synonym in synonyms[word]:
                    expanded_query = query.replace(word, synonym)
                    if expanded_query != query:
                        expansions.append(expanded_query)
        
        return expansions[:3]

class RealTimeNotificationManager:
    """实时通知管理器"""
    
    def __init__(self, socketio: SocketIO = None):
        self.socketio = socketio
        self.user_notifications = defaultdict(list)  # 用户通知
        self.notification_settings = defaultdict(dict)  # 通知设置
        self.online_users = set()  # 在线用户
        self.lock = threading.RLock()
        
    def set_socketio(self, socketio: SocketIO):
        """设置SocketIO实例"""
        self.socketio = socketio
    
    def add_notification(self, notification: Notification, send_immediately: bool = True):
        """添加通知"""
        with self.lock:
            self.user_notifications[notification.user_id].append(notification)
            
            # 保持最近100个通知
            if len(self.user_notifications[notification.user_id]) > 100:
                self.user_notifications[notification.user_id].pop(0)
        
        # 立即发送给在线用户
        if send_immediately and notification.user_id in self.online_users:
            self._send_notification(notification)
    
    def _send_notification(self, notification: Notification):
        """发送通知给客户端"""
        if not self.socketio:
            return
        
        try:
            # 检查用户通知设置
            settings = self.notification_settings.get(notification.user_id, {})
            notification_type = notification.notification_type.value
            
            if settings.get(f'enable_{notification_type}', True):
                self.socketio.emit('notification', {
                    'id': notification.id,
                    'type': notification.notification_type.value,
                    'title': notification.title,
                    'content': notification.content,
                    'created_at': notification.created_at.isoformat(),
                    'action_url': notification.action_url,
                    'metadata': notification.metadata
                }, room=f'user_{notification.user_id}')
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def mark_as_read(self, user_id: str, notification_id: str):
        """标记通知为已读"""
        with self.lock:
            for notification in self.user_notifications[user_id]:
                if notification.id == notification_id:
                    notification.read_at = datetime.now()
                    break
    
    def get_unread_notifications(self, user_id: str) -> List[Notification]:
        """获取未读通知"""
        with self.lock:
            return [
                notification for notification in self.user_notifications[user_id]
                if notification.read_at is None
            ]
    
    def get_notification_count(self, user_id: str) -> Dict[str, int]:
        """获取通知计数"""
        with self.lock:
            notifications = self.user_notifications[user_id]
            
            total_count = len(notifications)
            unread_count = sum(1 for n in notifications if n.read_at is None)
            
            # 按类型统计
            type_counts = defaultdict(int)
            for notification in notifications:
                type_counts[notification.notification_type.value] += 1
            
            return {
                'total': total_count,
                'unread': unread_count,
                'by_type': dict(type_counts)
            }
    
    def update_notification_settings(self, user_id: str, settings: Dict[str, Any]):
        """更新通知设置"""
        with self.lock:
            self.notification_settings[user_id].update(settings)
    
    def set_user_online(self, user_id: str):
        """设置用户在线"""
        with self.lock:
            self.online_users.add(user_id)
    
    def set_user_offline(self, user_id: str):
        """设置用户离线"""
        with self.lock:
            self.online_users.discard(user_id)

class UserExperienceOptimizer:
    """用户体验优化器主类"""
    
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.recommendation_engine = PersonalizedRecommendationEngine(self.behavior_analyzer)
        self.search_engine = SmartSearchEngine()
        self.notification_manager = RealTimeNotificationManager(socketio)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app, socketio=None):
        """初始化Flask应用"""
        self.app = app
        
        if socketio:
            self.notification_manager.set_socketio(socketio)
        
        # 注册请求钩子
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # 注册模板全局函数
        app.jinja_env.globals['get_recommendations'] = self.get_recommendations
        app.jinja_env.globals['get_unread_count'] = self.get_unread_notification_count
        
        logger.info("User experience optimizer initialized")
    
    def _before_request(self):
        """请求前处理"""
        # 设置用户在线状态
        user_id = session.get('userid')
        if user_id:
            self.notification_manager.set_user_online(str(user_id))
    
    def _after_request(self, response):
        """请求后处理"""
        # 记录用户行为
        user_id = session.get('userid')
        if user_id and request.endpoint:
            self._record_user_action(user_id, response)
        
        return response
    
    def _record_user_action(self, user_id: str, response):
        """记录用户行为"""
        try:
            # 确定行为类型
            action_type = UserActionType.VIEW
            if request.method == 'POST':
                if 'create' in request.endpoint:
                    action_type = UserActionType.CREATE
                elif 'update' in request.endpoint:
                    action_type = UserActionType.UPDATE
                elif 'delete' in request.endpoint:
                    action_type = UserActionType.DELETE
                elif 'like' in request.endpoint:
                    action_type = UserActionType.LIKE
                elif 'share' in request.endpoint:
                    action_type = UserActionType.SHARE
                elif 'comment' in request.endpoint:
                    action_type = UserActionType.COMMENT
            
            # 提取目标信息
            target_type = 'page'
            target_id = request.endpoint or 'unknown'
            
            # 从URL参数中提取更具体的目标信息
            if hasattr(request, 'view_args') and request.view_args:
                if 'article_id' in request.view_args:
                    target_type = 'article'
                    target_id = str(request.view_args['article_id'])
                elif 'user_id' in request.view_args:
                    target_type = 'user'
                    target_id = str(request.view_args['user_id'])
            
            # 构建元数据
            metadata = {
                'endpoint': request.endpoint,
                'method': request.method,
                'status_code': response.status_code,
                'response_time': getattr(g, 'start_time', time.time()) - time.time()
            }
            
            # 创建行为记录
            action = UserAction(
                user_id=str(user_id),
                action_type=action_type,
                timestamp=datetime.now(),
                target_type=target_type,
                target_id=target_id,
                metadata=metadata,
                session_id=session.get('session_id', 'unknown'),
                ip_address=request.remote_addr or '0.0.0.0',
                user_agent=request.headers.get('User-Agent', '')
            )
            
            self.behavior_analyzer.record_action(action)
            
        except Exception as e:
            logger.error(f"Error recording user action: {e}")
    
    def get_recommendations(self, user_id: str, content_type: str = 'article', limit: int = 5) -> List[Dict[str, Any]]:
        """获取推荐内容（模板函数）"""
        try:
            return self.recommendation_engine.recommend_content(str(user_id), content_type, limit)
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    def get_unread_notification_count(self, user_id: str) -> int:
        """获取未读通知数量（模板函数）"""
        try:
            counts = self.notification_manager.get_notification_count(str(user_id))
            return counts.get('unread', 0)
        except Exception as e:
            logger.error(f"Error getting notification count: {e}")
            return 0
    
    def send_notification(self, user_id: str, notification_type: NotificationType, 
                         title: str, content: str, action_url: str = None, 
                         metadata: Dict[str, Any] = None):
        """发送通知"""
        notification = Notification(
            id=hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest(),
            user_id=str(user_id),
            notification_type=notification_type,
            title=title,
            content=content,
            created_at=datetime.now(),
            read_at=None,
            action_url=action_url,
            metadata=metadata or {}
        )
        
        self.notification_manager.add_notification(notification)
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """获取用户分析数据"""
        try:
            activity_summary = self.behavior_analyzer.get_user_activity_summary(str(user_id))
            user_preference = self.behavior_analyzer.get_user_preference(str(user_id))
            notification_counts = self.notification_manager.get_notification_count(str(user_id))
            
            return {
                'activity_summary': activity_summary,
                'preferences': asdict(user_preference) if user_preference else {},
                'notification_counts': notification_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {}

# 全局用户体验优化器实例
_ux_optimizer = None

def get_ux_optimizer() -> UserExperienceOptimizer:
    """获取用户体验优化器实例"""
    global _ux_optimizer
    if _ux_optimizer is None:
        _ux_optimizer = UserExperienceOptimizer()
    return _ux_optimizer

def init_user_experience_optimization(app, socketio=None):
    """初始化用户体验优化系统"""
    try:
        ux_optimizer = get_ux_optimizer()
        ux_optimizer.init_app(app, socketio)
        
        logger.info("User experience optimization system initialized successfully")
        return ux_optimizer
        
    except Exception as e:
        logger.error(f"Failed to initialize user experience optimization system: {e}")
        raise

# 装饰器函数
def track_user_action(action_type: UserActionType, target_type: str = None):
    """用户行为跟踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 记录用户行为
            user_id = session.get('userid')
            if user_id:
                try:
                    ux_optimizer = get_ux_optimizer()
                    
                    action = UserAction(
                        user_id=str(user_id),
                        action_type=action_type,
                        timestamp=datetime.now(),
                        target_type=target_type or 'function',
                        target_id=func.__name__,
                        metadata={'function': func.__name__},
                        session_id=session.get('session_id', 'unknown'),
                        ip_address=request.remote_addr or '0.0.0.0',
                        user_agent=request.headers.get('User-Agent', '')
                    )
                    
                    ux_optimizer.behavior_analyzer.record_action(action)
                    
                except Exception as e:
                    logger.error(f"Error tracking user action: {e}")
            
            return result
        
        return wrapper
    return decorator 