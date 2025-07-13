"""Fuzzy Search Manager for finding documents by patient name similarity."""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher

from app.core.v1.mongodb_manager import MongoDBManager
from app.core.v1.exceptions import DatabaseException
from app.core.v1.log_manager import LogManager


class FuzzySearchManager:
    """
    Fuzzy Search Manager for finding documents by patient name similarity.
    
    Implements multiple search algorithms to find documents based on:
    - Exact matches
    - Partial matches (first characters, middle characters)
    - Phonetic similarity
    - Fuzzy string matching
    """
    
    def __init__(self):
        """Initialize Fuzzy Search Manager."""
        self.logger = LogManager(__name__)
        self.mongodb_manager = MongoDBManager()
        
        # Fuzzy search configuration
        self.min_similarity_score = 0.3  # Minimum similarity threshold
        self.max_results = 100  # Maximum results per search
        
        self.logger.info("Fuzzy Search Manager initialized successfully")
    
    def search_patients_by_name(
        self,
        search_term: str,
        user_id: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
        include_score: bool = True
    ) -> Dict[str, Any]:
        """
        Search for documents by patient name using fuzzy matching.
        
        Args:
            search_term: Patient name or partial name to search for
            user_id: Optional user filter
            limit: Maximum number of results
            skip: Number of results to skip
            include_score: Include similarity score in results
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            self.logger.info(
                "Starting fuzzy patient search",
                search_term=search_term,
                user_id=user_id,
                limit=limit,
                skip=skip
            )
            
            # Clean and normalize search term
            normalized_term = self._normalize_search_term(search_term)
            
            # Get all potential matches using multiple strategies
            candidates = self._get_search_candidates(normalized_term, user_id)
            
            # Score and rank candidates
            scored_results = self._score_candidates(normalized_term, candidates)
            
            # Filter by minimum score threshold
            filtered_results = [
                result for result in scored_results 
                if result['similarity_score'] >= self.min_similarity_score
            ]
            
            # Apply pagination
            total_found = len(filtered_results)
            paginated_results = filtered_results[skip:skip + limit]
            
            # Prepare response
            response = {
                "search_term": search_term,
                "normalized_term": normalized_term,
                "total_found": total_found,
                "documents": paginated_results,
                "limit": limit,
                "skip": skip,
                "search_strategies_used": [
                    "exact_match",
                    "text_search",
                    "prefix_match",
                    "substring_match",
                    "fuzzy_similarity"
                ],
                "min_similarity_threshold": self.min_similarity_score,
                "search_timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(
                "Fuzzy search completed",
                search_term=search_term,
                total_found=total_found,
                returned_count=len(paginated_results)
            )
            
            return response
            
        except Exception as err:
            self.logger.error(f"Fuzzy search failed: {err}")
            raise DatabaseException(f"Fuzzy search failed: {err}") from err
    
    def _normalize_search_term(self, search_term: str) -> str:
        """
        Normalize search term for better matching.
        
        Args:
            search_term: Raw search term
            
        Returns:
            Normalized search term
        """
        # Remove extra whitespace and convert to uppercase
        normalized = re.sub(r'\s+', ' ', search_term.strip().upper())
        
        # Remove special characters but keep spaces and commas
        normalized = re.sub(r'[^\w\s,]', '', normalized)
        
        return normalized
    
    def _get_search_candidates(self, normalized_term: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get potential document candidates using multiple search strategies.
        
        Args:
            normalized_term: Normalized search term
            user_id: Optional user filter
            
        Returns:
            List of candidate documents
        """
        candidates = []
        seen_ids = set()
        
        # Strategy 1: Exact match
        exact_matches = self._exact_match_search(normalized_term, user_id)
        for doc in exact_matches:
            if doc['_id'] not in seen_ids:
                candidates.append(doc)
                seen_ids.add(doc['_id'])
        
        # Strategy 2: MongoDB text search
        text_matches = self._text_search(normalized_term, user_id)
        for doc in text_matches:
            if doc['_id'] not in seen_ids:
                candidates.append(doc)
                seen_ids.add(doc['_id'])
        
        # Strategy 3: Prefix matching
        prefix_matches = self._prefix_search(normalized_term, user_id)
        for doc in prefix_matches:
            if doc['_id'] not in seen_ids:
                candidates.append(doc)
                seen_ids.add(doc['_id'])
        
        # Strategy 4: Substring matching
        substring_matches = self._substring_search(normalized_term, user_id)
        for doc in substring_matches:
            if doc['_id'] not in seen_ids:
                candidates.append(doc)
                seen_ids.add(doc['_id'])
        
        # Strategy 5: Get all documents for fuzzy comparison (limited)
        if len(candidates) < 50:  # Only if we don't have enough candidates
            all_docs = self._get_all_documents_for_fuzzy(user_id, limit=200)
            for doc in all_docs:
                if doc['_id'] not in seen_ids:
                    candidates.append(doc)
                    seen_ids.add(doc['_id'])
        
        return candidates
    
    def _exact_match_search(self, normalized_term: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for exact matches."""
        query = {"nombre_paciente": normalized_term}
        if user_id:
            query["user_id"] = user_id
        
        try:
            return self.mongodb_manager.search_documents(
                query=query,
                limit=50,
                sort=[("created_at", -1)]
            )
        except Exception as e:
            self.logger.warning(f"Exact match search failed: {e}")
            return []
    
    def _text_search(self, normalized_term: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search using MongoDB text index."""
        query = {"$text": {"$search": normalized_term}}
        if user_id:
            query["user_id"] = user_id
        
        try:
            return self.mongodb_manager.search_documents(
                query=query,
                limit=50,
                sort=[("score", {"$meta": "textScore"})]
            )
        except Exception as e:
            self.logger.warning(f"Text search failed: {e}")
            return []
    
    def _prefix_search(self, normalized_term: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for names that start with the search term."""
        query = {"nombre_paciente": {"$regex": f"^{re.escape(normalized_term)}", "$options": "i"}}
        if user_id:
            query["user_id"] = user_id
        
        try:
            return self.mongodb_manager.search_documents(
                query=query,
                limit=50,
                sort=[("created_at", -1)]
            )
        except Exception as e:
            self.logger.warning(f"Prefix search failed: {e}")
            return []
    
    def _substring_search(self, normalized_term: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for names that contain the search term."""
        query = {"nombre_paciente": {"$regex": re.escape(normalized_term), "$options": "i"}}
        if user_id:
            query["user_id"] = user_id
        
        try:
            return self.mongodb_manager.search_documents(
                query=query,
                limit=50,
                sort=[("created_at", -1)]
            )
        except Exception as e:
            self.logger.warning(f"Substring search failed: {e}")
            return []
    
    def _get_all_documents_for_fuzzy(self, user_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """Get all documents for fuzzy comparison."""
        query = {"medical_info_valid": True}
        if user_id:
            query["user_id"] = user_id
        
        try:
            return self.mongodb_manager.search_documents(
                query=query,
                limit=limit,
                sort=[("created_at", -1)]
            )
        except Exception as e:
            self.logger.warning(f"Get all documents failed: {e}")
            return []
    
    def _score_candidates(self, normalized_term: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score and rank candidates by similarity.
        
        Args:
            normalized_term: Normalized search term
            candidates: List of candidate documents
            
        Returns:
            List of scored and ranked documents
        """
        scored_results = []
        
        for doc in candidates:
            patient_name = doc.get('nombre_paciente', '').upper()
            
            if not patient_name:
                continue
            
            # Calculate similarity score
            similarity_score = self._calculate_similarity_score(normalized_term, patient_name)
            
            # Add score to document
            doc_with_score = doc.copy()
            doc_with_score['similarity_score'] = similarity_score
            doc_with_score['match_type'] = self._determine_match_type(normalized_term, patient_name)
            
            scored_results.append(doc_with_score)
        
        # Sort by similarity score (descending)
        scored_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return scored_results
    
    def _calculate_similarity_score(self, search_term: str, patient_name: str) -> float:
        """
        Calculate similarity score between search term and patient name.
        
        Args:
            search_term: Normalized search term
            patient_name: Patient name from document
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Exact match gets highest score
        if search_term == patient_name:
            return 1.0
        
        # Calculate multiple similarity metrics
        scores = []
        
        # 1. Sequence matcher similarity
        sequence_score = SequenceMatcher(None, search_term, patient_name).ratio()
        scores.append(sequence_score)
        
        # 2. Prefix similarity
        if patient_name.startswith(search_term):
            prefix_score = len(search_term) / len(patient_name)
            scores.append(prefix_score * 0.9)  # Slightly lower than exact match
        
        # 3. Substring similarity
        if search_term in patient_name:
            substring_score = len(search_term) / len(patient_name)
            scores.append(substring_score * 0.8)  # Lower than prefix
        
        # 4. Word-based similarity (for names with multiple words)
        search_words = search_term.split()
        patient_words = patient_name.split()
        
        if len(search_words) > 1 or len(patient_words) > 1:
            word_similarity = self._word_based_similarity(search_words, patient_words)
            scores.append(word_similarity)
        
        # 5. Character-based similarity (for partial names)
        char_similarity = self._character_based_similarity(search_term, patient_name)
        scores.append(char_similarity)
        
        # Return the highest score
        return max(scores) if scores else 0.0
    
    def _determine_match_type(self, search_term: str, patient_name: str) -> str:
        """Determine the type of match for debugging/display purposes."""
        if search_term == patient_name:
            return "exact"
        elif patient_name.startswith(search_term):
            return "prefix"
        elif search_term in patient_name:
            return "substring"
        else:
            return "fuzzy"
    
    def _word_based_similarity(self, search_words: List[str], patient_words: List[str]) -> float:
        """Calculate similarity based on word matching."""
        if not search_words or not patient_words:
            return 0.0
        
        matched_words = 0
        for search_word in search_words:
            for patient_word in patient_words:
                if search_word in patient_word or patient_word.startswith(search_word):
                    matched_words += 1
                    break
        
        return matched_words / len(search_words)
    
    def _character_based_similarity(self, search_term: str, patient_name: str) -> float:
        """Calculate similarity based on character matching."""
        if not search_term or not patient_name:
            return 0.0
        
        # Remove spaces and compare
        search_clean = search_term.replace(' ', '')
        patient_clean = patient_name.replace(' ', '')
        
        return SequenceMatcher(None, search_clean, patient_clean).ratio()
    
    def get_search_suggestions(self, partial_term: str, user_id: Optional[str] = None, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on partial input.
        
        Args:
            partial_term: Partial search term
            user_id: Optional user filter
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested patient names
        """
        try:
            normalized_term = self._normalize_search_term(partial_term)
            
            # Get suggestions using prefix search
            query = {"nombre_paciente": {"$regex": f"^{re.escape(normalized_term)}", "$options": "i"}}
            if user_id:
                query["user_id"] = user_id
            
            documents = self.mongodb_manager.search_documents(
                query=query,
                limit=limit * 2,  # Get more to account for duplicates
                sort=[("created_at", -1)]
            )
            
            # Extract unique patient names
            suggestions = []
            seen_names = set()
            
            for doc in documents:
                patient_name = doc.get('nombre_paciente', '').strip()
                if patient_name and patient_name not in seen_names:
                    suggestions.append(patient_name)
                    seen_names.add(patient_name)
                    
                    if len(suggestions) >= limit:
                        break
            
            return suggestions
            
        except Exception as err:
            self.logger.error(f"Get search suggestions failed: {err}")
            return [] 