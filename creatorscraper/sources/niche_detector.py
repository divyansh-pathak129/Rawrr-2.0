"""
Niche detection module for categorizing creators based on their content.
"""

import re
from typing import List, Dict, Tuple, Optional
from collections import Counter
from loguru import logger


class NicheDetector:
    """Detects creator niche based on bio, captions, and content analysis."""
    
    def __init__(self):
        """Initialize niche detector with predefined categories and keywords."""
        self.categories = {
            'Fitness': {
                'keywords': [
                    'fitness', 'workout', 'gym', 'exercise', 'training', 'muscle', 'strength',
                    'cardio', 'yoga', 'pilates', 'crossfit', 'bodybuilding', 'weightlifting',
                    'nutrition', 'protein', 'supplements', 'health', 'wellness', 'diet',
                    'personal trainer', 'coach', 'athlete', 'sports', 'running', 'cycling'
                ],
                'weight': 1.0
            },
            'Fashion': {
                'keywords': [
                    'fashion', 'style', 'outfit', 'clothing', 'dress', 'shoes', 'accessories',
                    'beauty', 'makeup', 'skincare', 'hair', 'styling', 'trend', 'designer',
                    'brand', 'shopping', 'retail', 'model', 'photoshoot', 'runway'
                ],
                'weight': 1.0
            },
            'Tech': {
                'keywords': [
                    'tech', 'technology', 'programming', 'coding', 'software', 'developer',
                    'engineer', 'ai', 'artificial intelligence', 'machine learning', 'data',
                    'startup', 'entrepreneur', 'innovation', 'gadgets', 'apps', 'digital',
                    'cybersecurity', 'blockchain', 'crypto', 'fintech', 'saas'
                ],
                'weight': 1.0
            },
            'Gaming': {
                'keywords': [
                    'gaming', 'gamer', 'streaming', 'twitch', 'youtube', 'esports', 'tournament',
                    'console', 'pc', 'playstation', 'xbox', 'nintendo', 'mobile games',
                    'strategy', 'rpg', 'fps', 'mmo', 'indie games', 'game development'
                ],
                'weight': 1.0
            },
            'Food': {
                'keywords': [
                    'food', 'cooking', 'recipe', 'chef', 'restaurant', 'cuisine', 'dining',
                    'baking', 'pastry', 'kitchen', 'ingredients', 'healthy eating', 'vegan',
                    'vegetarian', 'organic', 'farm to table', 'foodie', 'culinary', 'gastronomy'
                ],
                'weight': 1.0
            },
            'Travel': {
                'keywords': [
                    'travel', 'traveling', 'tourism', 'vacation', 'adventure', 'explore',
                    'destination', 'wanderlust', 'backpacking', 'solo travel', 'luxury travel',
                    'hotels', 'airbnb', 'flights', 'passport', 'visa', 'culture', 'photography'
                ],
                'weight': 1.0
            },
            'Business': {
                'keywords': [
                    'business', 'entrepreneur', 'startup', 'marketing', 'sales', 'finance',
                    'investment', 'consulting', 'strategy', 'leadership', 'management',
                    'networking', 'conference', 'speaker', 'mentor', 'coaching', 'success'
                ],
                'weight': 1.0
            },
            'Education': {
                'keywords': [
                    'education', 'learning', 'teaching', 'teacher', 'professor', 'student',
                    'university', 'college', 'course', 'tutorial', 'training', 'skill',
                    'knowledge', 'research', 'academic', 'scholar', 'degree', 'certification'
                ],
                'weight': 1.0
            },
            'Entertainment': {
                'keywords': [
                    'entertainment', 'comedy', 'actor', 'actress', 'performer', 'show',
                    'movie', 'film', 'tv', 'television', 'series', 'drama', 'comedy',
                    'music', 'singer', 'artist', 'celebrity', 'influencer', 'content creator'
                ],
                'weight': 1.0
            },
            'Lifestyle': {
                'keywords': [
                    'lifestyle', 'life', 'daily', 'routine', 'motivation', 'inspiration',
                    'mindfulness', 'meditation', 'self-care', 'productivity', 'organization',
                    'minimalism', 'sustainability', 'eco-friendly', 'home', 'family', 'relationships'
                ],
                'weight': 1.0
            },
            'Beauty': {
                'keywords': [
                    'beauty', 'makeup', 'skincare', 'cosmetics', 'skincare routine', 'tutorial',
                    'beauty tips', 'products', 'reviews', 'transformation', 'glow up',
                    'hair care', 'nail art', 'fashion', 'style', 'aesthetic'
                ],
                'weight': 1.0
            },
            'Health': {
                'keywords': [
                    'health', 'medical', 'doctor', 'nurse', 'healthcare', 'wellness',
                    'mental health', 'therapy', 'counseling', 'meditation', 'mindfulness',
                    'nutrition', 'diet', 'supplements', 'vitamins', 'wellness coach'
                ],
                'weight': 1.0
            },
            'Finance': {
                'keywords': [
                    'finance', 'money', 'investment', 'trading', 'stocks', 'crypto',
                    'budgeting', 'saving', 'debt', 'credit', 'banking', 'financial planning',
                    'wealth', 'retirement', 'insurance', 'tax', 'economy'
                ],
                'weight': 1.0
            },
            'Sports': {
                'keywords': [
                    'sports', 'athlete', 'team', 'competition', 'championship', 'league',
                    'football', 'soccer', 'basketball', 'tennis', 'golf', 'swimming',
                    'cycling', 'running', 'marathon', 'olympics', 'coach', 'training'
                ],
                'weight': 1.0
            },
            'Art': {
                'keywords': [
                    'art', 'artist', 'painting', 'drawing', 'sculpture', 'gallery',
                    'exhibition', 'creative', 'design', 'illustration', 'digital art',
                    'photography', 'visual', 'aesthetic', 'inspiration', 'portfolio'
                ],
                'weight': 1.0
            },
            'Music': {
                'keywords': [
                    'music', 'musician', 'singer', 'songwriter', 'producer', 'dj',
                    'concert', 'album', 'single', 'recording', 'studio', 'instrument',
                    'guitar', 'piano', 'drums', 'band', 'performance', 'live music'
                ],
                'weight': 1.0
            },
            'Parenting': {
                'keywords': [
                    'parenting', 'mom', 'dad', 'mother', 'father', 'family', 'kids',
                    'children', 'baby', 'toddler', 'parenting tips', 'childcare',
                    'education', 'activities', 'family life', 'work-life balance'
                ],
                'weight': 1.0
            },
            'DIY': {
                'keywords': [
                    'diy', 'craft', 'handmade', 'tutorial', 'project', 'home improvement',
                    'woodworking', 'sewing', 'knitting', 'crochet', 'pottery', 'jewelry',
                    'upcycling', 'repair', 'construction', 'tools', 'workshop'
                ],
                'weight': 1.0
            },
            'Photography': {
                'keywords': [
                    'photography', 'photographer', 'photo', 'camera', 'lens', 'shooting',
                    'portrait', 'landscape', 'wedding', 'event', 'studio', 'editing',
                    'photoshop', 'lightroom', 'equipment', 'technique', 'composition'
                ],
                'weight': 1.0
            }
        }
        
        logger.info(f"Initialized NicheDetector with {len(self.categories)} categories")
    
    def detect_niche(self, bio: str, captions: List[str] = None, posts: List[Dict] = None) -> Tuple[str, float]:
        """
        Detect niche based on bio and content.
        
        Args:
            bio: Creator's bio text
            captions: List of post captions
            posts: List of post data with captions
            
        Returns:
            Tuple of (niche, confidence_score)
        """
        if not bio and not captions and not posts:
            return 'Other', 0.0
        
        # Combine all text for analysis
        text_content = []
        
        if bio:
            text_content.append(bio.lower())
        
        if captions:
            text_content.extend([caption.lower() for caption in captions if caption])
        
        if posts:
            for post in posts:
                if isinstance(post, dict) and post.get('caption'):
                    text_content.append(post['caption'].lower())
        
        if not text_content:
            return 'Other', 0.0
        
        # Score each category
        category_scores = {}
        total_words = 0
        
        for category, config in self.categories.items():
            score = 0
            keywords = config['keywords']
            weight = config['weight']
            
            for text in text_content:
                words = re.findall(r'\b\w+\b', text)
                total_words += len(words)
                
                for word in words:
                    if word in keywords:
                        score += weight
            
            category_scores[category] = score
        
        # Find best category
        if not category_scores or max(category_scores.values()) == 0:
            return 'Other', 0.0
        
        best_category = max(category_scores, key=category_scores.get)
        max_score = category_scores[best_category]
        
        # Calculate confidence (normalize by total words)
        confidence = min(1.0, max_score / max(total_words, 1))
        
        logger.debug(f"Niche detection: {best_category} (confidence: {confidence:.3f})")
        return best_category, confidence
    
    def detect_multiple_niches(self, bio: str, captions: List[str] = None, posts: List[Dict] = None, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Detect multiple niches with confidence scores.
        
        Args:
            bio: Creator's bio text
            captions: List of post captions
            posts: List of post data with captions
            top_n: Number of top niches to return
            
        Returns:
            List of tuples (niche, confidence_score) sorted by confidence
        """
        if not bio and not captions and not posts:
            return [('Other', 0.0)]
        
        # Combine all text for analysis
        text_content = []
        
        if bio:
            text_content.append(bio.lower())
        
        if captions:
            text_content.extend([caption.lower() for caption in captions if caption])
        
        if posts:
            for post in posts:
                if isinstance(post, dict) and post.get('caption'):
                    text_content.append(post['caption'].lower())
        
        if not text_content:
            return [('Other', 0.0)]
        
        # Score each category
        category_scores = {}
        total_words = 0
        
        for category, config in self.categories.items():
            score = 0
            keywords = config['keywords']
            weight = config['weight']
            
            for text in text_content:
                words = re.findall(r'\b\w+\b', text)
                total_words += len(words)
                
                for word in words:
                    if word in keywords:
                        score += weight
            
            category_scores[category] = score
        
        # Sort by score and return top N
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for category, score in sorted_categories[:top_n]:
            confidence = min(1.0, score / max(total_words, 1))
            results.append((category, confidence))
        
        return results
    
    def get_category_keywords(self, category: str) -> List[str]:
        """
        Get keywords for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of keywords for the category
        """
        return self.categories.get(category, {}).get('keywords', [])
    
    def add_custom_category(self, category: str, keywords: List[str], weight: float = 1.0) -> None:
        """
        Add a custom category.
        
        Args:
            category: Category name
            keywords: List of keywords
            weight: Weight for keyword matching
        """
        self.categories[category] = {
            'keywords': keywords,
            'weight': weight
        }
        logger.info(f"Added custom category: {category} with {len(keywords)} keywords")
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.categories.keys())
