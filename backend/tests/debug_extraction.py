#!/usr/bin/env python3
"""
Debug the client name extraction
"""
import re

def debug_extract_client_name(message: str) -> str:
    """Debug version of extract client name"""
    print(f"🔍 Debugging message: '{message}'")
    message_lower = message.lower()
    
    # Known client names (in a real system, this would query the database)
    known_clients = ["acme", "techcorp", "global retail", "acme corporation"]
    
    for client in known_clients:
        if client in message_lower:
            print(f"✅ Found known client: {client}")
            # Return proper case
            if client == "acme":
                return "Acme Corporation"
            elif client == "techcorp":
                return "TechCorp"
            elif client == "global retail":
                return "Global Retail"
            else:
                return client.title()
    
    print("❌ No known clients found, trying regex patterns...")
    
    # Try to extract from common patterns - improved regex patterns
    patterns = [
        # More specific patterns for client names
        r"for\s+client\s+([A-Za-z][A-Za-z\s&.,'-]+?)(?:\s*\.|\s*,|\s*;|\s+it's|\s+with|\s+that|\s+who|\s*$)",
        r"client\s+([A-Za-z][A-Za-z\s&.,'-]+?)(?:\s*\.|\s*,|\s*;|\s+it's|\s+with|\s+that|\s+who|\s*$)",
        r"company\s+([A-Za-z][A-Za-z\s&.,'-]+?)(?:\s*\.|\s*,|\s*;|\s+it's|\s+with|\s+that|\s+who|\s*$)",
        # Pattern for "create contract for [ClientName]"
        r"contract\s+for\s+([A-Za-z][A-Za-z\s&.,'-]+?)(?:\s*\.|\s*,|\s*;|\s+it's|\s+with|\s+that|\s+who|\s*$)",
        # Pattern for company names with LLC, Inc, Corp, etc.
        r"([A-Za-z][A-Za-z\s&.,'-]*(?:LLC|Inc|Corp|Corporation|Ltd|Limited|Co|Company))\b",
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"🔍 Trying pattern {i+1}: {pattern}")
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            potential_name = match.group(1).strip()
            print(f"✅ Pattern {i+1} matched: '{potential_name}'")
            # Clean up the name
            potential_name = re.sub(r'\s+', ' ', potential_name)  # Remove extra spaces
            
            # Skip if it's too short or contains common stop words (but check as whole words, not substrings)
            stop_words = ["the", "and", "or", "with", "for", "that", "this", "a", "an"]
            potential_words = potential_name.lower().split()
            has_stop_words = any(word in stop_words for word in potential_words)
            
            print(f"🔍 Checking '{potential_name}': words={potential_words}, has_stop_words={has_stop_words}")
            
            if len(potential_name) > 2 and not has_stop_words:
                # Don't title case if it already has proper capitalization (like LLC)
                if any(word in potential_name for word in ["LLC", "Inc", "Corp", "Corporation", "Ltd", "Limited"]):
                    print(f"✅ Returning: '{potential_name}' (preserving case)")
                    return potential_name
                else:
                    result = potential_name.title()
                    print(f"✅ Returning: '{result}' (title case)")
                    return result
            else:
                print(f"❌ Rejected '{potential_name}' (too short or contains stop words)")
        else:
            print(f"❌ Pattern {i+1} didn't match")
    
    print("❌ No patterns matched")
    return ""

def debug_extract_contact_info(message: str):
    """Debug contact info extraction"""
    print(f"🔍 Debugging contact info in: '{message}'")
    
    contact_info = {
        'has_contact_info': False,
        'contact_name': None,
        'contact_email': None,
        'industry': None
    }
    
    # Extract email
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    email_match = re.search(email_pattern, message)
    if email_match:
        contact_info['contact_email'] = email_match.group(1)
        contact_info['has_contact_info'] = True
        print(f"✅ Found email: {contact_info['contact_email']}")
    else:
        print("❌ No email found")
    
    # Extract contact name (look for patterns like "with John Smith" or "contact Maria Black")
    name_patterns = [
        r'with\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'contact\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+as\s+the\s+contact'
    ]
    
    for i, pattern in enumerate(name_patterns):
        print(f"🔍 Trying name pattern {i+1}: {pattern}")
        match = re.search(pattern, message)
        if match:
            contact_info['contact_name'] = match.group(1)
            contact_info['has_contact_info'] = True
            print(f"✅ Found contact name: {contact_info['contact_name']}")
            break
        else:
            print(f"❌ Name pattern {i+1} didn't match")
    
    # Extract industry
    if 'startup' in message.lower():
        contact_info['industry'] = 'Startup'
        print("✅ Found industry: Startup")
    elif 'technology' in message.lower():
        contact_info['industry'] = 'Technology'
        print("✅ Found industry: Technology")
    elif 'manufacturing' in message.lower():
        contact_info['industry'] = 'Manufacturing'
        print("✅ Found industry: Manufacturing")
    else:
        print("❌ No industry found")
    
    print(f"📊 Final contact info: {contact_info}")
    return contact_info

if __name__ == "__main__":
    test_message = "create a new contract for client HealthPlus LLC. It's a startup firm with Maria Black as the contact, maria.black@hp.com. The contract starts on 1st Oct 2025 and ends on 31st Mar 2026. It's a fixed contract with original amount of $250,000, billing prompt date is 30th Nov 2025."
    
    print("=" * 80)
    print("DEBUGGING CLIENT NAME EXTRACTION")
    print("=" * 80)
    
    client_name = debug_extract_client_name(test_message)
    print(f"\n🎯 Final result: '{client_name}'")
    
    print("\n" + "=" * 80)
    print("DEBUGGING CONTACT INFO EXTRACTION")
    print("=" * 80)
    
    contact_info = debug_extract_contact_info(test_message)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Client Name: '{client_name}'")
    print(f"Has Contact Info: {contact_info['has_contact_info']}")
    print(f"Should trigger create_client_and_contract: {bool(client_name and contact_info['has_contact_info'])}")
