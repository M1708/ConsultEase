"""
Fuzzy client name matcher that uses database queries instead of regex patterns.
This approach is more robust and handles various user phrasings.
"""

import re
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.core.database import get_ai_db
from src.database.core.models import Client


class FuzzyClientMatcher:
    """Fuzzy client name matcher using database LIKE queries."""
    
    def __init__(self):
        # Simple patterns to extract potential client names
        self.client_extraction_patterns = [
            r"client\s+['\"]?([A-Za-z][A-Za-z\s&]{2,30})(?:\s+with|\s*$)['\"]?",
            r"for\s+client\s+['\"]?([A-Za-z][A-Za-z\s&]{2,30})(?:\s+with|\s*$)['\"]?",
            r"contract\s+with\s+['\"]?([A-Za-z][A-Za-z\s&]{2,30})(?:\s+with|\s*$)['\"]?",
            r"for\s+['\"]?([A-Za-z][A-Za-z\s&]{2,30})(?:\s+with|\s*$)['\"]?",
            # Additional patterns for more flexible matching
            r"client\s+([A-Za-z][A-Za-z\s&]{2,30})(?:\s|$|\.|,|;|:)",  # "client Sangard" without quotes
            r"for\s+([A-Za-z][A-Za-z\s&]{2,30})(?:\s|$|\.|,|;|:)",     # "for Sangard" without quotes
            r"with\s+([A-Za-z][A-Za-z\s&]{2,30})(?:\s|$|\.|,|;|:)",    # "with Sangard" without quotes
        ]
        
        # Patterns that should be excluded from client name extraction
        self.exclude_patterns = [
            r"file\s+attached",
            r"document\s+attached",
            r"attachment",
            r"upload",
            r"update\s+client",
            r"create\s+client",
            r"delete\s+client",
            r"with\s+no\s+next\s+billing",
            r"with\s+next\s+billing",
            r"with\s+upcoming\s+billing",
            r"with\s+amount\s+more\s+than",
            r"with\s+original\s+amount"
        ]
    
    def extract_potential_client_names(self, text: str) -> List[str]:
        """Extract potential client names from text using simple patterns."""
        potential_names = []
        
        for pattern in self.client_extraction_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                cleaned = match.strip().strip('"\'')
                
                # Skip if it matches exclude patterns
                if any(re.search(exclude_pattern, cleaned, re.IGNORECASE) for exclude_pattern in self.exclude_patterns):
                    continue
                
                # Skip if too short or too long
                if len(cleaned) < 3 or len(cleaned) > 50:
                    continue
                
                # Skip if it contains common non-client words (use word boundaries to avoid false positives)
                skip_words = ['with', 'that', 'where', 'having', 'billing', 'prompt', 'date', 'amount', 'more', 'than', 'contract', 'all', 'show', 'me']
                should_skip = False
                for word in skip_words:
                    # Use word boundaries to avoid false positives (e.g., "me" in "Acme")
                    if re.search(r'\b' + re.escape(word) + r'\b', cleaned.lower()):
                        should_skip = True
                        break
                if should_skip:
                    continue
                
                # Skip if it's mostly lowercase (likely not a company name)
                if cleaned.islower() and len(cleaned) > 5:
                    continue
                
                potential_names.append(cleaned)
        
        return list(set(potential_names))  # Remove duplicates
    
    async def find_matching_clients(self, potential_names: List[str]) -> List[Client]:
        """Find matching clients in the database using LIKE queries."""
        if not potential_names:
            return []
        
        try:
            async with get_ai_db() as session:
                matching_clients = []
                
                for name in potential_names:
                    # Create search patterns
                    search_patterns = [
                        f"%{name}%",  # Contains the name
                        f"{name}%",   # Starts with the name
                        f"%{name}",   # Ends with the name
                    ]
                    
                    # Try exact match first
                    try:
                        exact_match = await session.execute(
                            select(Client).where(func.lower(Client.client_name) == name.lower())
                        )
                        exact_clients = exact_match.scalars().all()
                        if exact_clients:
                            matching_clients.extend(exact_clients)
                            continue
                    except Exception as e:
                        print(f"🔍 DEBUG: Exact match failed for '{name}': {e}")
                    
                    # Try LIKE queries
                    for pattern in search_patterns:
                        try:
                            like_match = await session.execute(
                                select(Client).where(
                                    func.lower(Client.client_name).like(pattern.lower())
                                )
                            )
                            clients = like_match.scalars().all()
                            matching_clients.extend(clients)
                        except Exception as e:
                            print(f"🔍 DEBUG: LIKE query failed for pattern '{pattern}': {e}")
                
                # Remove duplicates and return
                unique_clients = list({client.client_id: client for client in matching_clients}.values())
                return unique_clients
        except Exception as e:
            print(f"🔍 DEBUG: Database error in find_matching_clients: {e}")
            return []
    
    async def find_best_client_match(self, text: str) -> Optional[Client]:
        """Find the best matching client for the given text."""
        potential_names = self.extract_potential_client_names(text)
        
        if not potential_names:
            return None
        
        matching_clients = await self.find_matching_clients(potential_names)
        
        if not matching_clients:
            return None
        
        # If only one match, return it
        if len(matching_clients) == 1:
            return matching_clients[0]
        
        # If multiple matches, try to find the best one
        # Priority: exact match > starts with > contains
        for name in potential_names:
            for client in matching_clients:
                client_name_lower = client.client_name.lower()
                name_lower = name.lower()
                
                if client_name_lower == name_lower:
                    return client
                elif client_name_lower.startswith(name_lower):
                    return client
        
        # If no exact or starts-with match, return the first one
        return matching_clients[0]
    
    def get_client_suggestions(self, matching_clients: List[Client]) -> str:
        """Generate client suggestions when multiple matches are found."""
        if not matching_clients:
            return ""
        
        if len(matching_clients) == 1:
            return f"Found client: {matching_clients[0].client_name}"
        
        suggestions = "Multiple clients found:\n"
        for i, client in enumerate(matching_clients, 1):
            suggestions += f"{i}. {client.client_name}\n"
        
        suggestions += "\nPlease specify which client you meant."
        return suggestions


# Global instance
fuzzy_matcher = FuzzyClientMatcher()
