"""
Tests for Supabase client operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from creatorscraper.storage.supabase_client import SupabaseClient
from creatorscraper.models.schemas import CreatorProfile, Post


class TestSupabaseClient:
    """Test Supabase client functionality."""
    
    def setup_method(self):
        """Setup test instance."""
        with patch('creatorscraper.storage.supabase_client.create_client'):
            self.client = SupabaseClient()
            self.client.client = Mock()
    
    def test_upsert_creator_success(self):
        """Test successful creator upsert."""
        # Create test profile
        profile = CreatorProfile(
            source='instagram',
            profile_url='https://www.instagram.com/test/',
            handle='test',
            display_name='Test User',
            bio='Test bio',
            niche='Tech',
            follower_count=1000,
            following_count=500,
            post_count=50
        )
        
        # Mock successful response
        self.client.client.table.return_value.upsert.return_value.execute.return_value.data = [{'id': 'test-id'}]
        
        result = self.client.upsert_creator(profile)
        
        assert result is True
        self.client.client.table.assert_called_once_with('creators')
    
    def test_upsert_creator_failure(self):
        """Test creator upsert failure."""
        # Create test profile
        profile = CreatorProfile(
            source='instagram',
            profile_url='https://www.instagram.com/test/',
            handle='test'
        )
        
        # Mock failed response
        self.client.client.table.return_value.upsert.return_value.execute.return_value.data = None
        
        result = self.client.upsert_creator(profile)
        
        assert result is False
    
    def test_upsert_creator_exception(self):
        """Test creator upsert with exception."""
        # Create test profile
        profile = CreatorProfile(
            source='instagram',
            profile_url='https://www.instagram.com/test/',
            handle='test'
        )
        
        # Mock exception
        self.client.client.table.return_value.upsert.return_value.execute.side_effect = Exception("Database error")
        
        result = self.client.upsert_creator(profile)
        
        assert result is False
    
    def test_get_creator_success(self):
        """Test successful creator retrieval."""
        # Mock successful response
        mock_data = {
            'id': 'test-id',
            'source': 'instagram',
            'profile_url': 'https://www.instagram.com/test/',
            'handle': 'test'
        }
        self.client.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_data]
        
        result = self.client.get_creator('https://www.instagram.com/test/')
        
        assert result == mock_data
        self.client.client.table.assert_called_once_with('creators')
    
    def test_get_creator_not_found(self):
        """Test creator retrieval when not found."""
        # Mock empty response
        self.client.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        result = self.client.get_creator('https://www.instagram.com/test/')
        
        assert result is None
    
    def test_get_creators_by_source(self):
        """Test getting creators by source."""
        # Mock response
        mock_data = [
            {'id': '1', 'source': 'instagram'},
            {'id': '2', 'source': 'instagram'}
        ]
        self.client.client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = mock_data
        
        result = self.client.get_creators_by_source('instagram', limit=10)
        
        assert result == mock_data
        assert len(result) == 2
    
    def test_get_creators_by_niche(self):
        """Test getting creators by niche."""
        # Mock response
        mock_data = [
            {'id': '1', 'niche': 'Tech'},
            {'id': '2', 'niche': 'Tech'}
        ]
        self.client.client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = mock_data
        
        result = self.client.get_creators_by_niche('Tech', limit=10)
        
        assert result == mock_data
        assert len(result) == 2
    
    def test_get_top_creators(self):
        """Test getting top creators."""
        # Mock response
        mock_data = [
            {'id': '1', 'follower_count': 10000},
            {'id': '2', 'follower_count': 5000}
        ]
        self.client.client.table.return_value.select.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_data
        
        result = self.client.get_top_creators(limit=10)
        
        assert result == mock_data
        assert len(result) == 2
    
    def test_get_creators_stats(self):
        """Test getting creators statistics."""
        # Mock responses for different queries
        self.client.client.table.return_value.select.return_value.execute.return_value.count = 100
        self.client.client.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 60
        self.client.client.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 40
        self.client.client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = [
            {'niche': 'Tech'}, {'niche': 'Tech'}, {'niche': 'Fitness'}
        ]
        
        result = self.client.get_creators_stats()
        
        assert result['total_creators'] == 100
        assert result['by_source']['instagram'] == 60
        assert result['by_source']['linkedin'] == 40
        assert result['by_niche']['Tech'] == 2
        assert result['by_niche']['Fitness'] == 1
    
    def test_delete_creator_success(self):
        """Test successful creator deletion."""
        # Mock successful response
        self.client.client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{'id': 'test-id'}]
        
        result = self.client.delete_creator('https://www.instagram.com/test/')
        
        assert result is True
        self.client.client.table.assert_called_once_with('creators')
    
    def test_delete_creator_not_found(self):
        """Test creator deletion when not found."""
        # Mock empty response
        self.client.client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
        
        result = self.client.delete_creator('https://www.instagram.com/test/')
        
        assert result is False
    
    def test_health_check_success(self):
        """Test successful health check."""
        # Mock successful response
        self.client.client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [{'id': 'test'}]
        
        result = self.client.health_check()
        
        assert result is True
    
    def test_health_check_failure(self):
        """Test health check failure."""
        # Mock exception
        self.client.client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("Connection error")
        
        result = self.client.health_check()
        
        assert result is False
