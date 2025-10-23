"""
Tests for niche detection module.
"""

import pytest
from creatorscraper.sources.niche_detector import NicheDetector


class TestNicheDetector:
    """Test niche detection functionality."""
    
    def setup_method(self):
        """Setup test instance."""
        self.detector = NicheDetector()
    
    def test_detect_niche_fitness(self):
        """Test fitness niche detection."""
        bio = "Fitness enthusiast, personal trainer, gym lover"
        niche, confidence = self.detector.detect_niche(bio)
        
        assert niche == "Fitness"
        assert confidence > 0.0
    
    def test_detect_niche_tech(self):
        """Test tech niche detection."""
        bio = "Software developer, AI researcher, startup founder"
        niche, confidence = self.detector.detect_niche(bio)
        
        assert niche == "Tech"
        assert confidence > 0.0
    
    def test_detect_niche_fashion(self):
        """Test fashion niche detection."""
        bio = "Fashion designer, style influencer, beauty blogger"
        niche, confidence = self.detector.detect_niche(bio)
        
        assert niche == "Fashion"
        assert confidence > 0.0
    
    def test_detect_niche_with_captions(self):
        """Test niche detection with post captions."""
        bio = "Content creator"
        captions = [
            "Check out this amazing workout routine! #fitness #gym",
            "Protein shake recipe for muscle building",
            "Gym motivation Monday! Let's get stronger"
        ]
        
        niche, confidence = self.detector.detect_niche(bio, captions)
        
        assert niche == "Fitness"
        assert confidence > 0.0
    
    def test_detect_niche_empty_input(self):
        """Test niche detection with empty input."""
        niche, confidence = self.detector.detect_niche("")
        
        assert niche == "Other"
        assert confidence == 0.0
    
    def test_detect_multiple_niches(self):
        """Test multiple niche detection."""
        bio = "Fitness coach and tech entrepreneur"
        captions = [
            "Morning workout complete! #fitness",
            "Building the next big startup #tech #entrepreneur"
        ]
        
        niches = self.detector.detect_multiple_niches(bio, captions, top_n=3)
        
        assert len(niches) == 3
        assert niches[0][0] in ["Fitness", "Tech", "Business"]
        assert all(conf >= 0.0 for _, conf in niches)
    
    def test_get_category_keywords(self):
        """Test getting category keywords."""
        keywords = self.detector.get_category_keywords("Fitness")
        
        assert isinstance(keywords, list)
        assert "fitness" in keywords
        assert "workout" in keywords
        assert "gym" in keywords
    
    def test_get_category_keywords_invalid(self):
        """Test getting keywords for invalid category."""
        keywords = self.detector.get_category_keywords("InvalidCategory")
        
        assert keywords == []
    
    def test_add_custom_category(self):
        """Test adding custom category."""
        custom_keywords = ["custom", "test", "example"]
        self.detector.add_custom_category("Custom", custom_keywords, weight=1.5)
        
        # Test detection with custom category
        bio = "This is a custom test example"
        niche, confidence = self.detector.detect_niche(bio)
        
        assert niche == "Custom"
        assert confidence > 0.0
    
    def test_get_all_categories(self):
        """Test getting all categories."""
        categories = self.detector.get_all_categories()
        
        assert isinstance(categories, list)
        assert "Fitness" in categories
        assert "Tech" in categories
        assert "Fashion" in categories
        assert len(categories) > 10  # Should have many categories
