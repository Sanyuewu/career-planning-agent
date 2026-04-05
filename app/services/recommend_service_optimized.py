# -*- coding: utf-8 -*-
"""
优化版推荐算法服务
目标：准确率提升15%，多样性提升10%，响应时间<200ms

核心优化：
1. 多阶段召回策略（规则+协同过滤+语义）
2. 特征工程优化（技能向量、行为特征、上下文特征）
3. 多样性控制（MMR算法）
4. 性能优化（并行计算、多级缓存）
"""

import math
import time
import logging
import asyncio
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RecommendMetrics:
    """推荐指标"""
    precision: float = 0.0
    recall: float = 0.0
    coverage: float = 0.0
    novelty: float = 0.0
    diversity: float = 0.0
    avg_response_ms: float = 0.0


@dataclass
class UserProfile:
    """用户画像特征"""
    user_id: str
    skills: List[str] = field(default_factory=list)
    skill_weights: Dict[str, float] = field(default_factory=dict)
    education_level: int = 0
    experience_years: float = 0.0
    career_intent: str = ""
    preferred_locations: List[str] = field(default_factory=list)
    preferred_salary_range: Tuple[float, float] = (0, 0)
    behavior_history: List[Dict] = field(default_factory=list)
    
    def to_feature_vector(self) -> Dict[str, float]:
        """转换为特征向量"""
        features = {}
        
        for skill, weight in self.skill_weights.items():
            features[f"skill_{skill}"] = weight
        
        features["education_level"] = self.education_level / 5.0
        features["experience_years"] = min(self.experience_years / 10.0, 1.0)
        
        if self.preferred_salary_range[1] > 0:
            features["salary_expectation"] = self.preferred_salary_range[1] / 50.0
        
        return features


@dataclass
class JobFeatures:
    """岗位特征"""
    job_id: str
    job_title: str
    required_skills: List[str] = field(default_factory=list)
    skill_importance: Dict[str, float] = field(default_factory=dict)
    salary_range: Tuple[float, float] = (0, 0)
    location: str = ""
    education_requirement: int = 0
    experience_requirement: float = 0.0
    popularity: float = 0.0
    category: str = ""
    
    def to_feature_vector(self) -> Dict[str, float]:
        """转换为特征向量"""
        features = {}
        
        for skill in self.required_skills:
            features[f"req_skill_{skill}"] = self.skill_importance.get(skill, 1.0)
        
        if self.salary_range[1] > 0:
            features["salary_max"] = self.salary_range[1] / 50.0
        features["popularity"] = min(self.popularity / 100.0, 1.0)
        features["edu_req"] = self.education_requirement / 5.0
        features["exp_req"] = min(self.experience_requirement / 10.0, 1.0)
        
        return features


class CollaborativeFilter:
    """
    协同过滤模块
    基于用户行为相似度进行推荐
    """
    
    def __init__(self):
        self._user_item_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._item_user_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._similarity_cache: Dict[str, Dict[str, float]] = {}
    
    def add_interaction(
        self, 
        user_id: str, 
        item_id: str, 
        score: float,
        interaction_type: str = "view"
    ):
        """添加用户-物品交互"""
        weight = {
            "view": 1.0,
            "click": 2.0,
            "apply": 5.0,
            "favorite": 3.0,
        }.get(interaction_type, 1.0)
        
        weighted_score = score * weight
        self._user_item_matrix[user_id][item_id] = weighted_score
        self._item_user_matrix[item_id][user_id] = weighted_score
        
        if user_id in self._similarity_cache:
            del self._similarity_cache[user_id]
    
    def compute_user_similarity(self, user_a: str, user_b: str) -> float:
        """计算用户相似度（余弦相似度）"""
        cache_key = f"{min(user_a, user_b)}_{max(user_a, user_b)}"
        
        items_a = self._user_item_matrix.get(user_a, {})
        items_b = self._user_item_matrix.get(user_b, {})
        
        if not items_a or not items_b:
            return 0.0
        
        common_items = set(items_a.keys()) & set(items_b.keys())
        if not common_items:
            return 0.0
        
        dot_product = sum(items_a[i] * items_b[i] for i in common_items)
        norm_a = math.sqrt(sum(v ** 2 for v in items_a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in items_b.values()))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def find_similar_users(self, user_id: str, k: int = 10) -> List[Tuple[str, float]]:
        """找到相似用户"""
        if user_id not in self._user_item_matrix:
            return []
        
        similarities = []
        for other_user in self._user_item_matrix:
            if other_user != user_id:
                sim = self.compute_user_similarity(user_id, other_user)
                if sim > 0:
                    similarities.append((other_user, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]
    
    def recommend_by_cf(
        self, 
        user_id: str, 
        exclude_items: Set[str],
        k: int = 20
    ) -> List[Tuple[str, float]]:
        """基于协同过滤推荐"""
        similar_users = self.find_similar_users(user_id, k=20)
        
        if not similar_users:
            return []
        
        item_scores: Dict[str, float] = defaultdict(float)
        
        for similar_user, similarity in similar_users:
            for item_id, score in self._user_item_matrix.get(similar_user, {}).items():
                if item_id not in exclude_items:
                    item_scores[item_id] += similarity * score
        
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:k]


class FeatureEngine:
    """
    特征工程模块
    提取和处理多维度特征
    """
    
    SKILL_EMBEDDINGS: Dict[str, List[float]] = {}
    
    SKILL_CATEGORIES = {
        'backend': {'java', 'python', 'go', 'node', 'spring', 'django', 'fastapi'},
        'frontend': {'javascript', 'vue', 'react', 'angular', 'html', 'css', 'typescript'},
        'database': {'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'},
        'devops': {'docker', 'kubernetes', 'jenkins', 'linux', 'nginx'},
        'ai_ml': {'tensorflow', 'pytorch', 'pandas', 'numpy', 'machine learning'},
        'mobile': {'android', 'ios', 'flutter', 'react native'},
        'data': {'spark', 'hadoop', 'hive', 'kafka', 'flink'},
    }
    
    @classmethod
    def extract_skill_features(cls, skills: List[str]) -> Dict[str, float]:
        """提取技能特征"""
        features = {}
        
        skill_weights = {
            '精通': 1.0, '熟练': 0.85, '掌握': 0.7, '熟悉': 0.6, '了解': 0.4
        }
        
        for skill in skills:
            clean_skill = skill.split('（')[0].split('(')[0].strip().lower()
            weight = 0.5
            
            for prof, w in skill_weights.items():
                if prof in skill:
                    weight = w
                    break
            
            features[f"skill_{clean_skill}"] = weight
            
            for category, cat_skills in cls.SKILL_CATEGORIES.items():
                if clean_skill in cat_skills or any(s in clean_skill for s in cat_skills):
                    features[f"cat_{category}"] = features.get(f"cat_{category}", 0) + weight
        
        return features
    
    @classmethod
    def compute_skill_match_score(
        cls, 
        user_skills: Dict[str, float],
        job_skills: List[str]
    ) -> float:
        """计算技能匹配分数"""
        if not job_skills:
            return 50.0  # 岗位无技能要求时给中性分，避免虚高
        
        matched_score = 0.0
        total_importance = 0.0
        
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            importance = 1.0
            total_importance += importance
            
            best_match = 0.0
            for user_skill, weight in user_skills.items():
                user_skill_lower = user_skill.lower()
                
                if user_skill_lower == job_skill_lower:
                    best_match = max(best_match, weight)
                elif user_skill_lower in job_skill_lower or job_skill_lower in user_skill_lower:
                    best_match = max(best_match, weight * 0.8)
                else:
                    for category, cat_skills in cls.SKILL_CATEGORIES.items():
                        if user_skill_lower in cat_skills and job_skill_lower in cat_skills:
                            best_match = max(best_match, weight * 0.6)
                            break
            
            matched_score += best_match * importance
        
        return min((matched_score / total_importance) * 100, 100) if total_importance > 0 else 50.0
    
    @classmethod
    def compute_context_features(
        cls,
        user: UserProfile,
        job: JobFeatures
    ) -> Dict[str, float]:
        """计算上下文特征"""
        features = {}
        
        if user.preferred_locations and job.location:
            loc_match = any(loc in job.location for loc in user.preferred_locations)
            features["location_match"] = 1.0 if loc_match else 0.0
        
        if user.preferred_salary_range[1] > 0 and job.salary_range[0] > 0:
            user_min, user_max = user.preferred_salary_range
            job_min, job_max = job.salary_range
            
            if job_max >= user_min and job_min <= user_max:
                features["salary_match"] = 1.0
            elif job_min >= user_max:
                features["salary_match"] = 0.5
            else:
                features["salary_match"] = 0.3
        
        edu_gap = user.education_level - job.education_requirement
        features["education_fit"] = min(max(edu_gap / 2.0 + 0.5, 0), 1.0)
        
        exp_gap = user.experience_years - job.experience_requirement
        features["experience_fit"] = min(max(exp_gap / 3.0 + 0.5, 0), 1.0)
        
        return features


class DiversityOptimizer:
    """
    多样性优化模块
    使用MMR算法提升推荐多样性
    """
    
    def __init__(self, lambda_param: float = 0.7):
        self.lambda_param = lambda_param
    
    def compute_item_similarity(
        self, 
        item_a: JobFeatures, 
        item_b: JobFeatures
    ) -> float:
        """计算物品相似度"""
        skills_a = set(s.lower() for s in item_a.required_skills)
        skills_b = set(s.lower() for s in item_b.required_skills)
        
        if not skills_a and not skills_b:
            return 0.0
        
        intersection = len(skills_a & skills_b)
        union = len(skills_a | skills_b)
        
        jaccard = intersection / union if union > 0 else 0.0
        
        category_match = 1.0 if item_a.category == item_b.category and item_a.category else 0.0
        
        return 0.7 * jaccard + 0.3 * category_match
    
    def mmr_rerank(
        self,
        candidates: List[Tuple[JobFeatures, float]],
        k: int = 10
    ) -> List[Tuple[JobFeatures, float]]:
        """
        MMR重排序
        Maximal Marginal Relevance算法
        """
        if not candidates:
            return []
        
        selected: List[Tuple[JobFeatures, float]] = []
        remaining = list(candidates)
        
        best = max(remaining, key=lambda x: x[1])
        selected.append(best)
        remaining.remove(best)
        
        while len(selected) < k and remaining:
            best_score = -float('inf')
            best_item = None
            
            for item, relevance in remaining:
                max_sim = 0.0
                for selected_item, _ in selected:
                    sim = self.compute_item_similarity(item, selected_item)
                    max_sim = max(max_sim, sim)
                
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_sim
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_item = (item, relevance)
            
            if best_item:
                selected.append(best_item)
                remaining.remove(best_item)
        
        return selected
    
    def compute_diversity_metrics(
        self, 
        recommendations: List[JobFeatures]
    ) -> Dict[str, float]:
        """计算多样性指标"""
        if len(recommendations) < 2:
            return {"coverage": 0, "novelty": 0, "diversity": 0}
        
        all_skills = set()
        for job in recommendations:
            all_skills.update(s.lower() for s in job.required_skills)
        
        coverage = len(all_skills)
        
        categories = []
        for job in recommendations:
            if job.category:
                categories.append(job.category)
        
        unique_categories = len(set(categories))
        total_with_category = len(categories)
        
        if total_with_category > 0:
            category_diversity = unique_categories / total_with_category
        else:
            category_diversity = 0.5
        
        novelty = min(unique_categories / max(len(recommendations) * 0.5, 1), 1.0)
        
        total_sim = 0.0
        count = 0
        for i, job_a in enumerate(recommendations):
            for job_b in recommendations[i+1:]:
                total_sim += self.compute_item_similarity(job_a, job_b)
                count += 1
        
        avg_sim = total_sim / count if count > 0 else 0
        diversity = 1 - avg_sim
        
        return {
            "coverage": coverage,
            "novelty": novelty,
            "diversity": diversity,
        }


class OptimizedRecommender:
    """
    优化版推荐器
    整合多阶段召回、特征工程、多样性优化
    """
    
    def __init__(self):
        self.cf = CollaborativeFilter()
        self.feature_engine = FeatureEngine()
        self.diversity_optimizer = DiversityOptimizer(lambda_param=0.5)
        self._job_cache: Dict[str, JobFeatures] = {}
        self._popularity_cache: Dict[str, float] = {}
    
    def build_user_profile(
        self,
        user_id: str,
        portrait: Dict,
        behavior_history: List[Dict] = None
    ) -> UserProfile:
        """构建用户画像"""
        skills = portrait.get("skills", [])
        skill_weights = {}
        
        proficiency_map = {
            '精通': 1.0, '熟练': 0.85, '掌握': 0.7, '熟悉': 0.6, '了解': 0.4
        }
        
        for skill in skills:
            clean_skill = skill.split('（')[0].split('(')[0].strip()
            weight = 0.5
            for prof, w in proficiency_map.items():
                if prof in skill:
                    weight = w
                    break
            skill_weights[clean_skill] = weight
        
        education = portrait.get("education", [{}])
        edu_level = 3
        if education:
            degree = education[0].get("degree", "本科") if education else "本科"
            edu_map = {"专科": 2, "本科": 3, "硕士": 4, "博士": 5}
            edu_level = edu_map.get(degree, 3)
        
        internships = portrait.get("internships", [])
        exp_years = sum(i.get("duration_months", 0) for i in internships) / 12.0
        
        career_intent = portrait.get("career_intent", "") or ""
        
        return UserProfile(
            user_id=user_id,
            skills=[s.split('（')[0].split('(')[0].strip() for s in skills],
            skill_weights=skill_weights,
            education_level=edu_level,
            experience_years=exp_years,
            career_intent=career_intent,
            behavior_history=behavior_history or [],
        )
    
    def build_job_features(
        self,
        job_id: str,
        job_data: Dict,
        popularity: float = 0.0
    ) -> JobFeatures:
        """构建岗位特征"""
        skills = job_data.get("skills", []) or job_data.get("required_skills", [])
        
        category = self._infer_category(job_data.get("job_name", ""), skills)
        
        return JobFeatures(
            job_id=job_id,
            job_title=job_data.get("job_name", job_id),
            required_skills=skills,
            skill_importance={s: 1.0 for s in skills},
            popularity=popularity,
            category=category,
        )
    
    def _infer_category(self, job_title: str, skills: List[str]) -> str:
        """推断岗位类别"""
        title_lower = job_title.lower()
        skills_lower = [s.lower() for s in skills]
        
        category_keywords = {
            'backend': ['后端', 'java', 'python', 'golang', '服务端', 'api', 'spring'],
            'frontend': ['前端', 'vue', 'react', 'angular', 'web', 'h5', 'css', 'javascript'],
            'mobile': ['移动', 'android', 'ios', 'app', 'flutter', '移动端'],
            'data': ['数据', '大数据', 'spark', 'hadoop', 'etl', '数据仓库'],
            'ai_ml': ['算法', '机器学习', 'ai', '深度学习', 'nlp', 'cv', '人工智能'],
            'devops': ['运维', 'devops', 'docker', 'k8s', 'sre', '容器'],
            'qa': ['测试', 'qa', '质量', '自动化测试'],
            'fullstack': ['全栈', 'fullstack'],
            'data_analyst': ['数据分析', '分析师', 'bi'],
        }
        
        for category, keywords in category_keywords.items():
            for kw in keywords:
                if kw in title_lower:
                    return category
            
            for skill in skills_lower:
                for kw in keywords:
                    if kw in skill:
                        return category
        
        return 'other'
    
    async def multi_stage_recall(
        self,
        user: UserProfile,
        job_pool: List[Dict],
        k: int = 50
    ) -> List[Tuple[Dict, float]]:
        """
        多阶段召回
        1. 规则召回（技能匹配）
        2. 协同过滤召回
        3. 热门召回
        """
        start_time = time.time()
        
        rule_candidates = self._rule_based_recall(user, job_pool, k)
        
        cf_candidates = []
        if user.behavior_history:
            cf_items = self.cf.recommend_by_cf(
                user.user_id, 
                set(c[0].get("job_name", "") for c in rule_candidates),
                k=20
            )
            for job_id, score in cf_items:
                for job in job_pool:
                    if job.get("job_name") == job_id:
                        cf_candidates.append((job, score * 0.8))
                        break
        
        popular_candidates = self._popularity_recall(job_pool, k=10)
        
        all_candidates: Dict[str, Tuple[Dict, float]] = {}
        
        for job, score in rule_candidates:
            job_name = job.get("job_name", "")
            if job_name not in all_candidates or all_candidates[job_name][1] < score:
                all_candidates[job_name] = (job, score)
        
        for job, score in cf_candidates:
            job_name = job.get("job_name", "")
            if job_name not in all_candidates:
                all_candidates[job_name] = (job, score * 0.7)
        
        for job, score in popular_candidates:
            job_name = job.get("job_name", "")
            if job_name not in all_candidates:
                all_candidates[job_name] = (job, score * 0.5)
        
        sorted_candidates = sorted(
            all_candidates.values(),
            key=lambda x: x[1],
            reverse=True
        )[:k]
        
        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"Multi-stage recall completed in {elapsed:.2f}ms, got {len(sorted_candidates)} candidates")
        
        return sorted_candidates
    
    def _rule_based_recall(
        self,
        user: UserProfile,
        job_pool: List[Dict],
        k: int
    ) -> List[Tuple[Dict, float]]:
        """规则召回"""
        candidates = []
        
        for job in job_pool:
            job_skills = job.get("skills", []) or job.get("required_skills", [])
            job_name = job.get("job_name", "")
            
            skill_score = FeatureEngine.compute_skill_match_score(
                user.skill_weights,
                job_skills
            )
            
            intent_score = 0.0
            if user.career_intent and user.career_intent in job_name:
                intent_score = 20.0
            
            total_score = skill_score + intent_score
            
            if total_score > 30:
                candidates.append((job, total_score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:k]
    
    def _popularity_recall(
        self,
        job_pool: List[Dict],
        k: int
    ) -> List[Tuple[Dict, float]]:
        """热门召回"""
        candidates = []
        
        for job in job_pool:
            popularity = job.get("popularity", 0) or self._popularity_cache.get(job.get("job_name", ""), 0)
            if popularity > 0:
                candidates.append((job, popularity))

        candidates.sort(key=lambda x: x[1], reverse=True)
        # 归一化到 0-100，避免原始计数值（如 4623）直接作为分数
        if candidates:
            max_pop = candidates[0][1]
            if max_pop > 100:
                candidates = [(job, round(pop / max_pop * 100, 2)) for job, pop in candidates]
        return candidates[:k]
    
    async def rank_candidates(
        self,
        user: UserProfile,
        candidates: List[Tuple[Dict, float]],
        match_service=None
    ) -> List[Tuple[JobFeatures, float]]:
        """候选排序"""
        ranked = []
        
        for job_data, initial_score in candidates:
            job_features = self.build_job_features(
                job_data.get("job_name", ""),
                job_data
            )
            
            context_features = FeatureEngine.compute_context_features(user, job_features)
            
            context_score = sum(context_features.values()) / len(context_features) if context_features else 0.5

            # 初始分数主导（90%），上下文微调（10%），保持区分度
            final_score = min(round(initial_score * 0.9 + context_score * 10, 2), 100)

            ranked.append((job_features, final_score))
        
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    async def recommend(
        self,
        user_id: str,
        portrait: Dict,
        job_pool: List[Dict],
        top_k: int = 10,
        diversity_weight: float = 0.3
    ) -> Tuple[List[Dict], RecommendMetrics]:
        """
        主推荐方法
        
        Returns:
            (recommendations, metrics)
        """
        start_time = time.time()
        
        user = self.build_user_profile(user_id, portrait)
        
        candidates = await self.multi_stage_recall(user, job_pool, k=50)

        if not candidates:
            return [], RecommendMetrics()

        # P1: 过滤用户明确排斥的岗位类型（preferences.rejected）
        rejected = (portrait.get("preferences") or {}).get("rejected") or []
        if rejected:
            _REJECT_KEYWORDS = {
                "前端": ["前端", "frontend", "vue", "react", "html"],
                "后端": ["后端", "backend", "java", "python", "服务端"],
                "算法": ["算法", "algorithm", "机器学习", "AI", "深度学习"],
                "运维": ["运维", "devops", "sre", "docker", "kubernetes"],
                "测试": ["测试", "test", "qa", "质量"],
                "产品": ["产品经理", "product", "pm"],
                "销售": ["销售", "business", "bd", "客户"],
                "游戏": ["游戏", "game"],
                "金融": ["金融", "finance", "银行", "证券"],
                "教育": ["教育", "education", "培训"],
            }
            before = len(candidates)
            filtered = []
            for jf, score in candidates:
                job_text = (jf.job_title or "").lower()
                is_rejected = False
                for category in rejected:
                    kws = _REJECT_KEYWORDS.get(category, [category.lower()])
                    if any(kw in job_text for kw in kws):
                        is_rejected = True
                        break
                if not is_rejected:
                    filtered.append((jf, score))
            candidates = filtered
            if before != len(candidates):
                logger.info("[Recommend] 排斥过滤: %d → %d（排斥类别: %s）",
                            before, len(candidates), rejected)

        ranked = await self.rank_candidates(user, candidates)

        diverse_ranked = self.diversity_optimizer.mmr_rerank(ranked, k=top_k)
        
        recommendations = []
        for job_features, score in diverse_ranked:
            recommendations.append({
                "job_id": job_features.job_id,
                "job_title": job_features.job_title,
                "score": round(score, 2),
                "category": job_features.category,
                "matched_skills": list(set(user.skills) & set(s.lower() for s in job_features.required_skills))[:5],
            })
        
        elapsed = (time.time() - start_time) * 1000
        
        diversity_metrics = self.diversity_optimizer.compute_diversity_metrics(
            [jf for jf, _ in diverse_ranked]
        )
        
        metrics = RecommendMetrics(
            coverage=diversity_metrics["coverage"],
            novelty=diversity_metrics["novelty"],
            diversity=diversity_metrics["diversity"],
            avg_response_ms=elapsed,
        )
        
        logger.info(f"Recommendation completed in {elapsed:.2f}ms, diversity={metrics.diversity:.3f}")
        
        return recommendations, metrics


optimized_recommender = OptimizedRecommender()
