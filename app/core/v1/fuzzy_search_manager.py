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
        self.min_similarity_score = 0.3  # Minimum similarity threshold (balanced for precision vs recall)
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
        # FIXED: Only do fuzzy comparison if we have very few candidates and the search term looks like a name
        if len(candidates) < 20 and self._looks_like_patient_name(normalized_term):
            all_docs = self._get_all_documents_for_fuzzy(user_id, limit=150)  # Increased for better fuzzy matching
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
        """Search using MongoDB text index on patient names only."""
        # FIXED: Instead of using $text which searches all indexed fields,
        # we use regex on nombre_paciente field to avoid matching medical content
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
        # FIXED: If search term doesn't look like a patient name, apply penalty
        if not self._looks_like_patient_name(search_term):
            # For medical terms, be much more strict
            # Only allow very high similarity scores (near exact matches)
            base_score = self._calculate_base_similarity_score(search_term, patient_name)
            if base_score < 0.9:  # Much higher threshold for medical terms
                return 0.0
            return base_score * 0.5  # Apply penalty even for high scores
        
        base_score = self._calculate_base_similarity_score(search_term, patient_name)
        
        # ADDITIONAL CHECK: For names that look valid but have no real connection
        # If the score is low and there's no actual substring/prefix match, be more strict
        if base_score < 0.5:  # Low similarity score
            # Check if there's any real connection (substring, prefix, or strong fuzzy match)
            has_real_connection = self._has_real_connection(search_term, patient_name)
            if not has_real_connection:
                # If no real connection and low score, reject it
                return 0.0
        
        return base_score
    
    def _has_real_connection(self, search_term: str, patient_name: str) -> bool:
        """
        Check if there's a real connection between search term and patient name.
        
        Args:
            search_term: Normalized search term
            patient_name: Patient name from document
            
        Returns:
            True if there's a meaningful connection, False otherwise
        """
        search_lower = search_term.lower()
        name_lower = patient_name.lower()
        
        # 1. Direct substring match
        if search_lower in name_lower:
            return True
        
        # 2. Prefix match with any word
        patient_words = name_lower.replace(',', ' ').split()
        for word in patient_words:
            if word.startswith(search_lower) and len(search_lower) >= 3:
                return True
        
        # 3. Strong fuzzy match with any word (>= 0.8 similarity)
        from difflib import SequenceMatcher
        for word in patient_words:
            if SequenceMatcher(None, search_lower, word).ratio() >= 0.8:
                return True
        
        # 4. Check if search term appears as part of any word (for compound names)
        for word in patient_words:
            if len(search_lower) >= 4 and search_lower in word:
                return True
        
        return False
    
    def _calculate_base_similarity_score(self, search_term: str, patient_name: str) -> float:
        """
        Calculate base similarity score between search term and patient name.
        
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
        # Apply stricter threshold for sequence matching, but be more permissive for names
        if self._looks_like_patient_name(search_term):
            # For legitimate names, be more permissive
            if sequence_score >= 0.6:
                scores.append(sequence_score)
            else:
                scores.append(sequence_score * 0.7)  # Less penalty for names
        else:
            # For medical terms, be very strict
            if sequence_score >= 0.8:
                scores.append(sequence_score)
            else:
                scores.append(sequence_score * 0.3)  # Heavy penalty for medical terms
        
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
        
        # 4b. Individual word matching (for partial name searches like "VANEZ" in "VANEZZA ALEJANDRA")
        if len(search_words) == 1 and len(patient_words) > 1:
            best_word_score = 0.0
            match_type = ""
            search_word = search_words[0]
            
            for patient_word in patient_words:
                # Remove punctuation from patient word
                clean_patient_word = patient_word.rstrip(',')
                
                # 1. HIGHEST PRIORITY: Exact word match
                if search_word == clean_patient_word:
                    best_word_score = 1.0  # Perfect score for exact matches
                    match_type = "exact_word"
                    break  # No need to check further
                
                # 2. HIGH PRIORITY: Fuzzy match (similar words)
                fuzzy_score = SequenceMatcher(None, search_word, clean_patient_word).ratio()
                if fuzzy_score >= 0.7:  # Strong fuzzy match threshold
                    if fuzzy_score > best_word_score:
                        best_word_score = fuzzy_score
                        match_type = "fuzzy"
                
                # 3. MEDIUM PRIORITY: Prefix match
                elif clean_patient_word.startswith(search_word) and len(search_word) >= 3:
                    prefix_score = len(search_word) / len(clean_patient_word)
                    # Boost score for legitimate prefix matches
                    if len(search_word) <= 4:  # Short prefixes like "ALE", "MAR"
                        boost_factor = 1.1
                    else:
                        boost_factor = 0.9
                    prefix_final = min(prefix_score * boost_factor, 0.85)  # Cap at 0.85 for prefixes
                    if prefix_final > best_word_score:
                        best_word_score = prefix_final
                        match_type = "prefix"
                
                # 4. LOWER PRIORITY: Substring match
                elif search_word in clean_patient_word and len(search_word) >= 3:
                    substring_score = len(search_word) / len(clean_patient_word)
                    # Moderate boost for substring matches
                    substring_final = min(substring_score * 1.2, 0.75)  # Cap at 0.75 for substrings
                    if substring_final > best_word_score:
                        best_word_score = substring_final
                        match_type = "substring"
            
            # Apply final score based on match type
            if best_word_score > 0:
                if match_type == "exact_word":
                    scores.append(1.0)  # Perfect score for exact word matches
                elif match_type == "fuzzy":
                    scores.append(best_word_score * 0.95)  # High score for fuzzy matches
                elif match_type == "prefix":
                    scores.append(best_word_score * 0.9)   # Good score for prefixes
                elif match_type == "substring":
                    scores.append(best_word_score * 0.8)   # Lower score for substrings
        
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
            best_match_score = 0.0
            for patient_word in patient_words:
                # Exact match gets full score
                if search_word == patient_word:
                    best_match_score = 1.0
                    break
                # Prefix match gets high score (more permissive for shorter terms)
                elif patient_word.startswith(search_word) and len(search_word) >= 3:
                    prefix_score = len(search_word) / len(patient_word)
                    # Give higher score for longer prefixes
                    if len(search_word) >= 4:
                        best_match_score = max(best_match_score, prefix_score * 0.9)
                    else:
                        best_match_score = max(best_match_score, prefix_score * 0.8)
                # Substring match gets lower score and requires longer terms
                elif search_word in patient_word and len(search_word) >= 4:
                    substring_score = len(search_word) / len(patient_word)
                    best_match_score = max(best_match_score, substring_score * 0.6)
            
            # Only count as matched if score is high enough
            if best_match_score >= 0.65:  # Slightly more permissive for legitimate fuzzy matching
                matched_words += best_match_score
        
        return matched_words / len(search_words)
    
    def _character_based_similarity(self, search_term: str, patient_name: str) -> float:
        """Calculate similarity based on character matching."""
        if not search_term or not patient_name:
            return 0.0
        
        # Remove spaces and compare
        search_clean = search_term.replace(' ', '')
        patient_clean = patient_name.replace(' ', '')
        
        return SequenceMatcher(None, search_clean, patient_clean).ratio()
    
    def _looks_like_patient_name(self, search_term: str) -> bool:
        """
        Determine if a search term looks like a patient name vs a medical term.
        
        Args:
            search_term: Normalized search term
            
        Returns:
            True if it looks like a patient name, False if it looks like a medical term
        """
        # Convert to lowercase for analysis
        term_lower = search_term.lower()
        
        # Medical terms that should NOT trigger fuzzy search
        medical_keywords = {
            'cardio', 'cardiolo', 'cardiología', 'cardiology',
            'otorrinolaringología', 'otorrinolaringologia', 'otolaryngology',
            'rinitis', 'faringitis', 'laringitis',
            'diagnóstico', 'diagnostico', 'diagnosis',
            'hospital', 'consulta', 'emergencia',
            'medicamento', 'medicina', 'tratamiento',
            'ibuprofeno', 'paracetamol', 'azitromicina',
            'síntoma', 'sintoma', 'enfermedad',
            'terapia', 'cirugía', 'cirugia', 'operación',
            'análisis', 'analisis', 'examen', 'estudio',
            'radiografía', 'radiografia', 'tomografía',
            'ultrasonido', 'resonancia', 'biopsia',
            'neurología', 'neurologia', 'neurology',
            'psiquiatría', 'psiquiatria', 'psychiatry',
            'pediatría', 'pediatria', 'pediatrics',
            'ginecología', 'ginecologia', 'gynecology',
            'urología', 'urologia', 'urology',
            'dermatología', 'dermatologia', 'dermatology'
        }
        
        # Check if the term is a known medical keyword
        if term_lower in medical_keywords:
            return False
        
        # Check if it contains medical suffixes/prefixes
        medical_patterns = [
            'ología', 'ologia',  # cardiología, neurología
            'itis',              # rinitis, faringitis
            'grama', 'grafía',   # electrocardiograma, radiografía
            'scopia', 'scopía',  # endoscopia, laparoscopia
            'tomía', 'tomia',    # traqueotomía, lobotomía
            'patía', 'patia',    # cardiopatía, neuropatía
            'terapia',           # fisioterapia, quimioterapia
            'logía', 'logia',    # cardiología, neurología (alternative)
        ]
        
        for pattern in medical_patterns:
            if pattern in term_lower:
                return False
        
        # If it has typical name patterns, it's likely a name
        name_patterns = [
            ',',  # "GARCIA, MARIA" format
            ' DE ', ' DEL ', ' LA ',  # Spanish name particles
            ' Y ', ' E ',  # Name connectors
        ]
        
        for pattern in name_patterns:
            if pattern in search_term.upper():
                return True
        
        # If it's a single word with 2+ characters and doesn't match medical patterns,
        # it could be a name (like "GARCIA", "MARIA", "PEDRO", "VANEZ")
        if len(search_term.strip()) >= 2 and ' ' not in search_term.strip():
            # Additional check: if it's all uppercase or title case, more likely a name
            if search_term.isupper() or search_term.istitle():
                return True
            # Also consider mixed case or lowercase as potential names
            if search_term.isalpha():  # Only letters, no numbers or special chars
                return True
        
        # If it has multiple words and doesn't match medical patterns, likely a name
        if len(search_term.split()) >= 2:
            return True
        
        # Default to True for ambiguous cases (be permissive with names)
        return True
    
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