from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, Optional
import traceback
from src.database.core.database import get_ai_db
import base64

from datetime import datetime
import time
from src.auth.dependencies import get_current_user, AuthenticatedUser
import json
import re
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
# --- New Imports for LangGraph Integration ---
from src.aiagents.graph.hybrid_workflow import app as agent_app
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from src.aiagents.graph.state import create_initial_state
from src.auth.session_manager import SessionManager
from src.database.core.models import Client

router = APIRouter()

# 🚀 REMOVED: is_employee_fast_path_query function to align with agentic AI principles
# TODO: If employee queries become too slow, consider re-implementing this function
# All employee queries now go through the regular agent graph like clients and contracts

# 🚀 REMOVED: extract_employee_search_term function to align with agentic AI principles
# TODO: If employee search becomes less accurate, consider re-implementing this function
# The agent now handles search term extraction naturally through its instructions

# 🚀 REMOVED: fast_employee_search function to align with agentic AI principles
# TODO: If employee queries become too slow, consider re-implementing this function
# All employee queries now go through the regular agent graph like clients and contracts

def _normalize_message_roles(messages):
    """Normalize message roles to OpenAI-compatible format"""
    if not messages:
        return messages

    normalized_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            # Create a copy to avoid modifying the original
            normalized_msg = msg.copy()

            # Normalize role from 'human' to 'user'
            if normalized_msg.get('role') == 'human':
                normalized_msg['role'] = 'user'
                print(f"🔧 Normalized message role from 'human' to 'user' for message: {normalized_msg.get('content', '')[:50]}...")

            # Also normalize type if it exists
            if normalized_msg.get('type') == 'human':
                normalized_msg['type'] = 'user'

            normalized_messages.append(normalized_msg)
        else:
            normalized_messages.append(msg)

    return normalized_messages

def _make_serializable(obj, max_depth=10, current_depth=0):
    """Convert OpenAI objects to JSON-serializable format with depth protection"""
    if current_depth >= max_depth:
        return str(obj)  # Prevent infinite recursion

    if hasattr(obj, 'model_dump'):
        # Pydantic models
        try:
            return obj.model_dump()
        except Exception:
            return str(obj)
    elif hasattr(obj, '__dict__'):
        # OpenAI ChatCompletionMessage objects
        if hasattr(obj, 'content') and hasattr(obj, 'role'):
            result = {
                'role': obj.role,
                'content': obj.content,
                'type': getattr(obj, 'type', 'assistant')
            }
            # Handle tool_calls safely
            if hasattr(obj, 'tool_calls') and obj.tool_calls:
                try:
                    result['tool_calls'] = _make_serializable(obj.tool_calls, max_depth, current_depth + 1)
                except Exception:
                    result['tool_calls'] = []
            return result
        else:
            # Generic object with __dict__
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):  # Skip private attributes
                    try:
                        result[key] = _make_serializable(value, max_depth, current_depth + 1)
                    except Exception:
                        result[key] = str(value)
            return result
    elif isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            try:
                # Ensure key is hashable
                if isinstance(key, (str, int, float, bool, type(None))):
                    result[key] = _make_serializable(value, max_depth, current_depth + 1)
                else:
                    result[str(key)] = _make_serializable(value, max_depth, current_depth + 1)
            except Exception:
                result[str(key)] = str(value)
        return result
    elif isinstance(obj, (list, tuple)):
        result = []
        for item in obj:
            try:
                result.append(_make_serializable(item, max_depth, current_depth + 1))
            except Exception:
                result.append(str(item))
        return result
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Fallback to string representation for any other type
        try:
            return str(obj)
        except Exception:
            return "<unserializable_object>"

def _make_serializable_state(state):
    """Ensure all values in the state are hashable and serializable"""
    if not isinstance(state, dict):
        return state

    serializable_state = {}
    for key, value in state.items():
        try:
            # Ensure key is hashable
            if isinstance(key, (str, int, float, bool, type(None))):
                hashable_key = key
            else:
                hashable_key = str(key)

            # Make value serializable and ensure no unhashable types
            serializable_value = _make_serializable(value)

            # Additional check: ensure no nested dictionaries are used as keys
            if isinstance(serializable_value, dict):
                serializable_value = _ensure_no_dict_keys(serializable_value)

            serializable_state[hashable_key] = serializable_value
        except Exception as e:
            print(f"Warning: Could not serialize state key '{key}': {e}")
            # Use string representation as fallback
            serializable_state[str(key)] = str(value)

    return serializable_state

def _ensure_no_dict_keys(obj, max_depth=5, current_depth=0):
    """Recursively ensure no dictionaries are used as keys anywhere in the object"""
    if current_depth >= max_depth:
        return str(obj) if not isinstance(obj, (str, int, float, bool, type(None))) else obj

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            # Convert any non-hashable key to string
            if isinstance(key, dict):
                hashable_key = str(key)
            elif isinstance(key, (list, tuple)):
                hashable_key = str(key)
            elif isinstance(key, (str, int, float, bool, type(None))):
                hashable_key = key
            else:
                hashable_key = str(key)

            # Recursively process the value
            result[hashable_key] = _ensure_no_dict_keys(value, max_depth, current_depth + 1)
        return result
    elif isinstance(obj, (list, tuple)):
        return [_ensure_no_dict_keys(item, max_depth, current_depth + 1) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # For any other object, try to make it serializable
        try:
            return _make_serializable(obj)
        except:
            return str(obj)

def _validate_state_hashable(state, path="root", max_depth=10, current_depth=0):
    """Recursively validate that all values in the state are hashable"""
    if current_depth >= max_depth:
        return  # Prevent infinite recursion

    if isinstance(state, dict):
        for key, value in state.items():
            # Check if key is hashable
            try:
                hash(key)
            except TypeError as e:
                raise TypeError(f"Unhashable key at {path}.{key}: {type(key).__name__} - {e}")

            # Recursively validate the value
            _validate_state_hashable(value, f"{path}.{key}", max_depth, current_depth + 1)

    elif isinstance(state, (list, tuple)):
        for i, item in enumerate(state):
            _validate_state_hashable(item, f"{path}[{i}]", max_depth, current_depth + 1)

    elif isinstance(state, (str, int, float, bool, type(None))):
        # These are hashable
        pass

    else:
        # For other objects, try to hash them
        try:
            hash(state)
        except TypeError as e:
            raise TypeError(f"Unhashable value at {path}: {type(state).__name__} - {e}")

class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    agent: str
    success: bool
    timestamp: str
    session_id: str
    workflow_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@router.post("/greeting")
async def fast_greeting(chat_request: ChatRequest, request: Request):
    """
    Ultra-fast greeting endpoint with optional user personalization.
    """
    start_time = time.perf_counter()
    
    try:
        print(f"FAST GREETING ENDPOINT: Request received at {datetime.now()}")
        
        message_content = chat_request.message
        
        # Default response
        greeting_response = "Hello! How can I help you today?"
        session_id = "fast-greeting"
        
        # Optional user personalization
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                
                async with get_ai_db() as session:
                    current_user = await get_current_user(credentials, session)
                    
                    # Extract first name for personalized greeting
                    user_name = current_user.user.full_name or current_user.user.email
                    first_name = user_name.split()[0] if user_name else ''
                    
                    if first_name:
                        greeting_response = f"Hello {first_name}! How can I help you today?"
                    
                    session_id = current_user.session_id
                    print(f"FAST GREETING: Personalized for {first_name}")
                
        except Exception as auth_error:
            # Auth failure doesn't break the endpoint
            print(f"FAST GREETING: Auth failed, using generic greeting: {auth_error}")
        
        # Return response
        response = ChatResponse(
            response=greeting_response,
            agent="Milo",
            success=True,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            workflow_id=f"workflow_{datetime.now().timestamp()}",
            data={
                "processing_time": {"greeting": f"{(time.perf_counter() - start_time) * 1000:.2f}ms"},
                "status": "ultra_fast_greeting"
            }
        )
        
        end_time = time.perf_counter()
        print(f"FAST GREETING ENDPOINT: Completed in {(end_time - start_time) * 1000:.2f}ms")
        
        return response
        
    except Exception as e:
        end_time = time.perf_counter()
        print(f"Fast greeting failed after {(end_time - start_time) * 1000:.2f}ms: {e}")
        
        return ChatResponse(
            response="Hello! How can I help you today?",
            agent="Milo",
            success=True,
            timestamp=datetime.now().isoformat(),
            session_id="fast-greeting",
            workflow_id=f"workflow_{datetime.now().timestamp()}",
            data={
                "processing_time": {"greeting": f"{(time.perf_counter() - start_time) * 1000:.2f}ms"},
                "status": "ultra_fast_greeting_fallback"
            }
        )

@router.post("/clients")
async def fast_clients(chat_request: ChatRequest, request: Request):
    """
    Ultra-fast client listing endpoint that bypasses LangGraph for simple queries.
    """
    start_time = time.perf_counter()
    
    try:
        print(f"FAST CLIENTS ENDPOINT: Request received at {datetime.now()}")
        
        message_content = chat_request.message
        
        # Authentication
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        async with get_ai_db() as session:
            current_user = await get_current_user(credentials, session)
            
            # Get all clients using async query
            result = await session.execute(
                select(Client).order_by(Client.client_name)
            )
            clients = result.scalars().all()
            
            client_list = []
            for client in clients:
                client_list.append({
                    "client_id": client.client_id,
                    "client_name": client.client_name,
                    "industry": client.industry,
                    "primary_contact_name": client.primary_contact_name,
                    "primary_contact_email": client.primary_contact_email,
                    "company_size": client.company_size,
                    "created_at": str(client.created_at) if client.created_at else None
                })
            
            # Format response message
            if len(client_list) == 0:
                response_message = "No clients found in the system."
            else:
                response_message = f"Here are all {len(client_list)} clients in the system with detailed information:\n\n"
                for i, client in enumerate(client_list, 1):
                    response_message += f"**{i}. {client['client_name']}**\n"
                    
                    if client['industry']:
                        response_message += f"   • Industry: {client['industry']}\n"
                    
                    if client['company_size']:
                        response_message += f"   • Company Size: {client['company_size']}\n"
                    
                    if client['primary_contact_name']:
                        response_message += f"   • Primary Contact: {client['primary_contact_name']}"
                        if client['primary_contact_email']:
                            response_message += f" ({client['primary_contact_email']})"
                        response_message += "\n"
                    elif client['primary_contact_email']:
                        response_message += f"   • Contact Email: {client['primary_contact_email']}\n"
                    
                    if client['created_at']:
                        response_message += f"   • Added: {client['created_at'][:10]}\n"
                    
                    response_message += "\n"
            
            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000
            
            response = ChatResponse(
                response=response_message,
                agent="Milo",
                success=True,
                timestamp=datetime.now().isoformat(),
                session_id=current_user.session_id,
                workflow_id=f"workflow_{datetime.now().timestamp()}",
                data={
                    "processing_time": {"clients": f"{processing_time:.2f}ms"},
                    "status": "ultra_fast_clients",
                    "clients": client_list,
                    "count": len(client_list)
                }
            )
            
            print(f"FAST CLIENTS ENDPOINT: Completed in {processing_time:.2f}ms")
            return response
            
    except Exception as e:
        end_time = time.perf_counter()
        print(f"Fast clients failed after {(end_time - start_time) * 1000:.2f}ms: {e}")
        return ChatResponse(
            response=f"I encountered an error retrieving clients: {str(e)}",
            agent="Milo",
            success=False,
            timestamp=datetime.now().isoformat(),
            session_id="error-session",
            data={
                "processing_time": {"clients": f"{(time.perf_counter() - start_time) * 1000:.2f}ms"},
                "status": "ultra_fast_clients_error",
                "error": str(e)
            }
        )

@router.post("/message-with-file")
async def send_chat_message_with_file(
    request: Request,
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    session_id: str = Form(...)
):
    """
    Enhanced chat endpoint that handles file uploads with messages for agentic document management.
    """
    print(f"🚀 CHAT API: message-with-file endpoint called with message: {message}")
    try:
        if not message:
            raise HTTPException(status_code=400, detail="Message content is required.")
        
        # Authentication
        print(f"🔍 DEBUG: Received message: {message[:100]}...")
        print(f"🔍 DEBUG: Session ID: {session_id}")
        print(f"🔍 DEBUG: File provided: {file.filename if file else 'None'}")
        
        # Get authenticated user
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Use a separate database session for authentication
        print(f"🔍 DEBUG: Starting authentication process")
        async with get_ai_db() as auth_db:
            print(f"🔍 DEBUG: Got auth database session")
            current_user = await get_current_user(credentials, auth_db)
            print(f"🔍 DEBUG: Authentication successful for user: {current_user.user_id}")
        
        # Now use the main database session for the rest of the function
        async with get_ai_db() as db:
            # Handle file upload if provided
            file_data = None
            file_info = None
            if file and file.filename:
                # Read file content
                file_content = await file.read()
                print(f"🔍 DEBUG: Raw file content length: {len(file_content)} bytes")
                
                file_data = base64.b64encode(file_content).decode('utf-8')
                print(f"🔍 DEBUG: Base64 encoded length: {len(file_data)}")
                
                # Create file info for the agent
                file_info = {
                    "filename": file.filename,
                    "mime_type": file.content_type or "application/octet-stream",
                    "file_data": file_data,
                    "file_size": len(file_content)
                }
                print(f"🔍 DEBUG: File processed - {file.filename} ({len(file_content)} bytes)")
                print(f"🔍 DEBUG: File info file_data length: {len(file_info['file_data'])}")
                
                # Add file context to the message
                message = f"{message}\n\n[File attached: {file.filename} ({file_info['file_size']} bytes)]"
            
            # Create enhanced chat request with file info
            enhanced_request = ChatRequest(
                message=message,
                session_id=session_id,
                file_info=file_info
            )
            
            # Process through regular chat flow (inline implementation)
            message_content = enhanced_request.message
            if not message_content:
                raise HTTPException(status_code=400, detail="Message content is required.")

            # ULTRA-FAST greeting detection BEFORE any dependencies
            message_lower = message_content.lower().strip()
            
            # Simple and explicit greeting detection
            simple_greetings = ["hi", "hello", "hey", "hola", "howdy", "greetings"]
            greeting_phrases = ["good morning", "good afternoon", "good evening", "good night"]
            
            is_greeting = (
                message_lower in simple_greetings or
                any(message_lower.startswith(g + ' ') for g in simple_greetings) or
                any(phrase in message_lower for phrase in greeting_phrases) or
                "my name is" in message_lower
            )
            
            if is_greeting:
                return {
                    "response": f"Hello! I'm Milo, your ConsultEase AI assistant. How can I help you today?",
                    "agent": "Milo",
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "workflow_id": None,
                    "data": {"status": "greeting_detected"}
                }

            # Get or create session
            session_manager = SessionManager()
            existing_state = None
            user_id = str(current_user.user_id)
            try:
                print(f"🔍 DEBUG: Attempting to retrieve conversation state for session {session_id}, user {user_id}")
                existing_state = await session_manager.get_chat_session(session_id, user_id)
                print(f"🔍 DEBUG: Raw session data retrieved: {existing_state}")
                print(f"🔍 DEBUG: Type of retrieved data: {type(existing_state)}")
                
                if existing_state and "conversation_state" in existing_state:
                    existing_state = existing_state["conversation_state"]
                    print(f"🔄 CHAT API: Found existing conversation state for session {session_id}")
                    print(f"🔍 DEBUG: Conversation state data: {existing_state.get('data', {})}")
                else:
                    existing_state = None
                    print(f"🔄 CHAT API: No existing conversation state found")
                    print(f"🔍 DEBUG: existing_state is None: {existing_state is None}")
                    if existing_state:
                        print(f"🔍 DEBUG: existing_state keys: {list(existing_state.keys()) if isinstance(existing_state, dict) else 'Not a dict'}")
            except Exception as e:
                print(f"🔄 CHAT API: Exception during session retrieval: {e}")
                print(f"🔍 DEBUG: Exception type: {type(e)}")
                import traceback
                print(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
                existing_state = None
            
            # Create or update state
            if existing_state:
                # Add new message to existing conversation - use dict format with 'user' type
                new_message = {
                    "type": "user",
                    "content": message_content,
                    "role": "user"
                }
                existing_state["messages"].append(new_message)
                
                # Update context
                existing_state["context"]["last_interaction"] = datetime.now().isoformat()
                existing_state["context"]["interaction_count"] = existing_state["context"].get("interaction_count", 0) + 1
                existing_state["status"] = "processing"
                
                initial_state = existing_state
                print(f"🔄 CHAT API: Updated existing state, now has {len(initial_state['messages'])} messages")
            else:
                # Create new conversation state
                initial_message = HumanMessage(content=message_content)
                initial_state = create_initial_state(
                    user_id=user_id,
                    session_id=session_id,
                    user_name=current_user.user.full_name or current_user.user.email,
                    user_role=current_user.role,
                    initial_message=initial_message
                )
                
                print(f"🔄 CHAT API: Created new conversation state")
            
            # Add file_info to context if provided
            if hasattr(enhanced_request, 'file_info') and enhanced_request.file_info:
                print(f"🔍 DEBUG: Adding file_info to context - file_data length: {len(enhanced_request.file_info.get('file_data', ''))}")
                print(f"🔍 DEBUG: File_info keys: {list(enhanced_request.file_info.keys())}")
                initial_state["context"]["file_info"] = enhanced_request.file_info

            # Process through agent graph
            print(f"🔍 DEBUG: File upload - Invoking agent with recursion_limit=20")
            print(f"🔍 DEBUG: File upload - Initial state keys: {list(initial_state.keys())}")
            print(f"🔍 DEBUG: File upload - Context keys: {list(initial_state.get('context', {}).keys())}")
            result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 20})
            print(f"🔍 DEBUG: File upload - Agent invocation completed")
            
            # TODO: ERROR HANDLING - Extract the response from the result and check for errors
            if result and "messages" in result and len(result["messages"]) > 0:
                last_message = result["messages"][-1]
                print(f"🔍 CHAT API (FILE): Last message type: {type(last_message)}")
                print(f"🔍 CHAT API (FILE): Last message: {last_message}")
                
                if hasattr(last_message, 'content'):
                    response_text = last_message.content
                    print(f"🔍 CHAT API (FILE): Extracted content from object message: {response_text[:100]}...")
                elif isinstance(last_message, dict) and 'content' in last_message:
                    response_text = last_message['content']
                    print(f"🔍 CHAT API (FILE): Extracted content from dict message: {response_text[:100]}...")
                else:
                    response_text = str(last_message)
                    print(f"🔍 CHAT API (FILE): Using string conversion: {response_text[:100]}...")
                
                # TODO: ERROR HANDLING - Check if the response indicates an error
                is_error = any(error_indicator in response_text for error_indicator in [
                    "❌ No employee found",
                    "❌ Invalid file data", 
                    "❌ User context not available",
                    "❌ Error",
                    "Failed to",
                    "Recursion limit"
                ])
            else:
                response_text = "I'm sorry, I couldn't process your request. Please try again."
                is_error = True
            
            # Determine the agent name
            agent_name = "Milo"
            if "agent" in result.get("context", {}):
                agent_name = result["context"]["agent"]
            
            # Save the updated state
            try:
                # Convert result to serializable format before saving
                serializable_result = _make_serializable(result)
                print(f"🔍 DEBUG: Saving conversation state with data: {serializable_result.get('data', {})}")
                print(f"🔍 DEBUG: Session ID: {session_id}, User ID: {current_user.user_id}")
                print(f"🔍 DEBUG: Full serializable_result keys: {list(serializable_result.keys())}")

                # Save conversation state to session using the same session_id as retrieval
                await session_manager.store_chat_session(
                    session_id,  # Use the same session_id as retrieval
                    str(current_user.user_id),
                    {"conversation_state": serializable_result}
                )
                print(f"🔍 DEBUG: Conversation state saved successfully")
                print(f"🔄 CHAT API: Saved conversation state with {len(serializable_result.get('messages', []))} messages")
            except Exception as e:
                print(f"⚠️ CHAT API: Failed to save conversation state: {e}")
                import traceback
                print(f"🔍 DEBUG: Save error traceback: {traceback.format_exc()}")
            
            # TODO: ERROR HANDLING - Return success: false for errors to trigger frontend clearing
            print(f"🔍 CHAT API (FILE): Final response being returned:")
            print(f"🔍 CHAT API (FILE): - response: {response_text[:100]}...")
            print(f"🔍 CHAT API (FILE): - response type: {type(response_text)}")
            print(f"🔍 CHAT API (FILE): - response length: {len(str(response_text))}")
            print(f"🔍 CHAT API (FILE): - success: {not is_error}")
            
            return ChatResponse(
                response=response_text,
                agent=agent_name,
                success=not is_error,  # TODO: ERROR HANDLING - Set success based on error detection
                timestamp=datetime.now().isoformat(),
                session_id=session_id,
                workflow_id=result.get("workflow_id"),
                data=result.get("data", {})
            )
            
    except Exception as e:
        print(f"❌ Chat processing with file failed: {str(e)}")
        return ChatResponse(
            response=f"I encountered an error processing your request with file: {str(e)}",
            agent="error_handler",
            success=False,
            timestamp=datetime.now().isoformat(),
            session_id="error-session",
            data={"error": str(e)}
        )

@router.post("/message")
async def send_chat_message(chat_request: ChatRequest, request: Request):
    """
    Sends a message to the new agentic graph and returns a JSON response.
    """
    print(f"🔥 CHAT API: ENTRY POINT - Message received: {chat_request.message}")
    print(f"🔥 CHAT API: Session ID: {chat_request.session_id}")
    
    #db = next(get_db())
    
    try:
        message_content = chat_request.message
        if not message_content:
            raise HTTPException(status_code=400, detail="Message content is required.")

        # Authentication - outside database session to avoid nested sessions
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Use a separate database session for authentication
        async with get_ai_db() as auth_db:
            current_user = await get_current_user(credentials, auth_db)
        
        # Now use the main database session for the rest of the function
        async with get_ai_db() as db:
            # ULTRA-FAST greeting detection AFTER authentication
            message_lower = message_content.lower().strip()
            
            # Simple and explicit greeting detection
            simple_greetings = ["hi", "hello", "hey", "hola", "howdy", "greetings"]
            greeting_phrases = ["good morning", "good afternoon", "good evening", "good night"]
            
            is_greeting = (
                message_lower in simple_greetings or
                any(message_lower.startswith(g + ' ') for g in simple_greetings) or
                any(phrase in message_lower for phrase in greeting_phrases) or
                "my name is" in message_lower
            )
            
            if is_greeting:
                print(f"🔥 CHAT API: ULTRA-FAST GREETING PATH!")
                print(f"🔍 DEBUG: Greeting detected - {message_content}")
                
                # Extract first name for personalized greeting
                first_name = ''
                if "my name is" in message_lower:
                    try:
                        # Find the start of the name in the original message
                        # by finding "my name is" case-insensitively
                        match_pos = message_content.lower().find("my name is")
                        if match_pos != -1:
                            name_start_pos = match_pos + len("my name is")
                            first_name = message_content[name_start_pos:].strip()
                    except:
                        pass
                
                # Use authenticated user's name if no name provided
                if not first_name:
                    user_name = current_user.user.full_name or current_user.user.email
                    first_name = user_name.split()[0] if user_name else ''
                
                greeting_response = f"Hello{(' ' + first_name) if first_name else ''}! How can I help you today?"
                print(f"🔥 CHAT API: Greeting response: {greeting_response}")
                
                return ChatResponse(
                    response=greeting_response,
                    agent="Milo",
                    success=True,
                    timestamp=datetime.now().isoformat(),
                    session_id=current_user.session_id,
                    workflow_id=f"workflow_{datetime.now().timestamp()}",
                    data={
                        "processing_time": {"greeting": "< 0.01s"},
                        "status": "ultra_fast_greeting"
                    }
                )
            
            # 🚀 PHASE 2 OPTIMIZATION: Detect simple informational queries that can be answered quickly
            # TODO: If complex queries are incorrectly identified as simple, revert these optimizations
            simple_info_queries = [
                "what is", "what are", "tell me about", "explain", "how does", "how do",
                "what does", "what can", "what should", "what would", "is it", "are you"
            ]
            
            is_simple_info_query = (
                any(query in message_lower for query in simple_info_queries) and
                len(message_content.split()) <= 10 and  # Short queries only
                not any(complex_word in message_lower for complex_word in [
                    "create", "add", "update", "delete", "modify", "change", "edit",
                    "contract", "employee", "client", "deliverable", "time", "expense"
                ])
            )
            
            if is_simple_info_query:
                print(f"🔥 CHAT API: ULTRA-FAST SIMPLE INFO PATH!")
                return ChatResponse(
                    response="I'm here to help with your consulting business needs. You can ask me about clients, contracts, employees, deliverables, time tracking, or expenses. What would you like to know?",
                    agent="Milo",
                    success=True,
                    timestamp=datetime.now().isoformat(),
                    session_id="fast-simple-info",
                    workflow_id=f"workflow_{datetime.now().timestamp()}",
                    data={
                        "processing_time": {"simple_info": "< 0.01s"},
                        "status": "ultra_fast_simple_info"
                    }
                )
            
            # 🚀 REMOVED: Fast path for employee queries to maintain consistency with other agents
            # TODO: If employee queries become too slow, consider re-implementing fast path
            # All employee queries now go through the regular agent graph like clients and contracts
            
            # ULTRA-FAST client listing detection - but check for complex queries first
            client_queries = [
                "show all clients", "list all clients", "get all clients", "all clients",
                "show clients", "list clients", "get clients", "clients list",
                "what clients do we have", "who are our clients", "client list"
            ]
            
            # Check for complex client queries that need full LangGraph processing
            complex_client_queries = [
                "clients with contracts", "clients and contracts", "clients along with contracts",
                "show clients with their contracts", "list clients and their contracts",
                "clients with their contracts", "all clients with their contracts",
                "show me all clients with their contracts", "show all clients with contracts"
            ]
            
            is_complex_client_query = any(query in message_lower for query in complex_client_queries)
            is_simple_client_list = any(query in message_lower for query in client_queries) and not is_complex_client_query
            
            if is_simple_client_list:
                print(f"🔥 CHAT API: ULTRA-FAST CLIENT LIST PATH!")
                # Redirect to fast clients endpoint
                return await fast_clients(request)
            
            # For non-fast-path messages, proceed with LangGraph
            print(f"🔥 CHAT API: Processing complex query...")
            print(f"🔍 DEBUG: Regular message - {message_content[:100]}...")
            print(f"🔍 DEBUG: Session ID: {chat_request.session_id}")
            
            print(f"🔥 CHAT API: Proceeding with LangGraph...")
            print(f"🔥 CHAT API: Message '{message_content}' did not match any fast paths")

            # --- LangGraph Invocation for complex messages ---
            # 1. Load existing conversation context or create new one
            
            session_manager = SessionManager()
            user_id = str(current_user.user_id)
            session_id = chat_request.session_id or current_user.session_id
            
            # Try to load existing conversation state
            existing_state = None
            print(f"🔥 CHAT API: About to retrieve session data for session_id={session_id}, user_id={user_id}")
            try:
                chat_session_data = await session_manager.get_chat_session(
                    session_id, 
                    user_id
                )
                print(f"🔍 DEBUG: Raw chat session data: {chat_session_data}")
                if chat_session_data and "conversation_state" in chat_session_data:
                    existing_state = chat_session_data["conversation_state"]

                    # Normalize message roles to fix OpenAI API compatibility
                    if existing_state.get('messages'):
                        existing_state['messages'] = _normalize_message_roles(existing_state['messages'])

                    print(f"🔄 CHAT API: Loaded existing conversation state with {len(existing_state.get('messages', []))} messages")
                    print(f"🔍 DEBUG: Existing state data: {existing_state.get('data', {})}")
                else:
                    print(f"🔍 DEBUG: No conversation_state in chat_session_data")
            except Exception as e:
                print(f"🔄 CHAT API: No existing state found, creating new: {e}")
            
            # Create or update state
            if existing_state:
                # Add new message to existing conversation - use dict format with 'user' type
                new_message = {
                    "type": "user",
                    "content": message_content,
                    "role": "user"
                }
                existing_state["messages"].append(new_message)
                
                # Update context
                existing_state["context"]["last_interaction"] = datetime.now().isoformat()
                existing_state["context"]["interaction_count"] = existing_state["context"].get("interaction_count", 0) + 1
                existing_state["status"] = "processing"
                
                # Add database to context
                #existing_state["context"]["database"] = db
                
                initial_state = existing_state
                print(f"🔄 CHAT API: Updated existing state, now has {len(initial_state['messages'])} messages")
            else:
                # Create new conversation state
                initial_message = HumanMessage(content=message_content)
                initial_state = create_initial_state(
                    user_id=user_id,
                    session_id=session_id,
                    user_name=current_user.user.full_name or current_user.user.email,
                    user_role=current_user.role,
                    initial_message=initial_message
                )
                
            # Add database to context (removed to avoid unhashable type error)
            #initial_state["context"]["database"] = db
                print(f"🔄 CHAT API: Created new conversation state")
            
            # Add file_info to context if provided
            if hasattr(chat_request, 'file_info') and chat_request.file_info:
                initial_state["context"]["file_info"] = chat_request.file_info

            # Ensure all messages are properly serializable
            if initial_state.get("messages"):
                serializable_messages = []
                for msg in initial_state["messages"]:
                    if hasattr(msg, 'type') and hasattr(msg, 'content'):
                        # LangChain message object - convert to dict
                        serializable_messages.append({
                            "type": msg.type,
                            "content": msg.content,
                            "role": getattr(msg, 'role', msg.type)
                        })
                    elif isinstance(msg, dict):
                        # Already a dict - ensure it's properly structured
                        if 'type' not in msg:
                            msg['type'] = msg.get('role', 'user')
                        if 'role' not in msg:
                            msg['role'] = msg.get('type', 'user')
                        serializable_messages.append(msg)
                    else:
                        # Fallback - convert to string
                        serializable_messages.append({
                            "type": "unknown",
                            "content": str(msg),
                            "role": "unknown"
                        })
                initial_state["messages"] = serializable_messages

            # Ensure all state values are hashable/serializable - ULTRA AGGRESSIVE APPROACH
            print(f"🔍 DEBUG: Before serialization - state keys: {list(initial_state.keys())}")

            # First, make everything serializable
            initial_state = _make_serializable_state(initial_state)
            print(f"🔍 DEBUG: After first serialization - state keys: {list(initial_state.keys())}")

            # Second pass - ensure no dictionaries are used as keys anywhere
            initial_state = _ensure_no_dict_keys(initial_state)
            print(f"🔍 DEBUG: After second pass - state keys: {list(initial_state.keys())}")

            # Third pass - validate hashability
            try:
                _validate_state_hashable(initial_state)
                print("✅ State validation passed - all values are hashable")
            except Exception as validation_error:
                print(f"❌ State validation failed: {validation_error}")
                # Create a minimal state as fallback
                initial_state = {
                    "messages": [{"type": "user", "content": message_content, "role": "user"}],
                    "current_agent": "router",
                    "data": {},
                    "status": "routing",
                    "context": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "user_name": f"{current_user.user.first_name} {current_user.user.last_name}".strip() or current_user.user.email,
                        "user_role": current_user.role,
                        "conversation_start": datetime.now().isoformat(),
                        "last_interaction": datetime.now().isoformat(),
                        "interaction_count": 1
                    }
                }
                print("✅ Created minimal fallback state")

            # DEBUG: Add additional validation before LangGraph invocation
            try:
                # Validate that all state values are hashable
                _validate_state_hashable(initial_state)
                print("✅ State validation passed - all values are hashable")
            except Exception as validation_error:
                print(f"❌ State validation failed: {validation_error}")
                # Continue anyway, but log the issue

            # 🚀 PHASE 2 OPTIMIZATION: Reduced recursion limit to prevent multiple iterations
            # TODO: If agent responses become incomplete or tools don't execute properly, revert recursion_limit to 10
            print(f"🔍 DEBUG: Invoking agent with recursion_limit=20")
            print(f"🔍 DEBUG: Initial state keys: {list(initial_state.keys())}")
            print(f"🔍 DEBUG: Context keys: {list(initial_state.get('context', {}).keys())}")

            # 🚀 PHASE 2 OPTIMIZATION: Reduced recursion limit to prevent multiple iterations
            # TODO: If agent responses become incomplete or tools don't execute properly, revert recursion_limit to 10
            try:
                result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 20})
                print(f"🔍 DEBUG: Agent invocation completed successfully")
            except Exception as langgraph_error:
                print(f"❌ LangGraph invocation failed: {langgraph_error}")
                # Try with minimal state as last resort
                try:
                    minimal_state = {
                        "messages": [{"type": "user", "content": message_content, "role": "user"}],
                        "current_agent": "router",
                        "data": {},
                        "status": "routing",
                        "context": {
                            "user_id": user_id,
                            "session_id": session_id,
                            "user_name": f"{current_user.user.first_name} {current_user.user.last_name}".strip() or current_user.user.email,
                            "user_role": current_user.role,
                            "conversation_start": datetime.now().isoformat(),
                            "last_interaction": datetime.now().isoformat(),
                            "interaction_count": 1
                        }
                    }
                    print("🔄 Trying with minimal state...")
                    result = await agent_app.ainvoke(minimal_state, config={"recursion_limit": 5})
                    print(f"✅ Minimal state invocation successful")
                except Exception as minimal_error:
                    print(f"❌ Minimal state also failed: {minimal_error}")
                    # Create a fallback result structure
                    result = {
                        "messages": [{"content": "I'm sorry, I encountered an error processing your request. Please try again.", "role": "assistant"}],
                        "context": {
                            "user_id": user_id,
                            "session_id": session_id,
                            "agent": "error_handler"
                        },
                        "data": {},
                        "status": "error"
                    }
                    print("✅ Created fallback result structure")

            print(f"🔍 DEBUG: Agent invocation completed")
            
            # 3. Extract the response from the result
            response_content = "I'm processing your request..."

            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                print(f"🔍 DEBUG: Last message type: {type(last_message)}")
                print(f"🔍 DEBUG: Last message: {last_message}")

                if hasattr(last_message, 'content'):
                    response_content = last_message.content
                    print(f"🔍 DEBUG: Extracted content from LangChain message: {response_content[:100]}...")
                elif isinstance(last_message, dict) and 'content' in last_message:
                    # Check if this is a tool result message
                    if last_message.get('role') == 'tool' and last_message.get('name'):
                        print(f"🔍 CHAT API: Tool result message detected - name: {last_message.get('name')}")
                        try:
                            # Parse the JSON content from tool result
                            import json
                            tool_result = json.loads(last_message['content'])
                            if isinstance(tool_result, dict) and 'message' in tool_result:
                                response_content = tool_result['message']
                                print(f"🔍 CHAT API: Extracted message from tool result: {response_content[:100]}...")
                            else:
                                response_content = last_message['content']
                                print(f"🔍 CHAT API: Tool result is not dict or no message field, using raw content: {response_content[:100]}...")
                        except (json.JSONDecodeError, TypeError) as e:
                            response_content = last_message['content']
                            print(f"🔍 CHAT API: Failed to parse tool result JSON, using raw content: {response_content[:100]}...")
                    else:
                        response_content = last_message['content']
                        print(f"🔍 CHAT API: Extracted content from dict message: {response_content[:100]}...")
                    
                    print(f"🔍 CHAT API: Dict message keys: {list(last_message.keys())}")
                    if 'data' in last_message:
                        print(f"🔍 CHAT API: Message has data field with keys: {list(last_message['data'].keys()) if isinstance(last_message['data'], dict) else 'Not a dict'}")
                    else:
                        print(f"🔍 CHAT API: Message has no data field")
                else:
                    # Fallback - convert to string and try to extract content
                    last_message_str = str(last_message)
                    print(f"🔍 DEBUG: Last message as string: {last_message_str[:200]}...")

                    # Try to parse as JSON if it looks like a dict
                    if last_message_str.startswith("{") and "content" in last_message_str:
                        try:
                            import json
                            parsed = json.loads(last_message_str)
                            if isinstance(parsed, dict) and 'content' in parsed:
                                response_content = parsed['content']
                                print(f"🔍 DEBUG: Extracted content from JSON string: {response_content[:100]}...")
                        except:
                            response_content = last_message_str
                    else:
                        response_content = last_message_str

            print(f"🔍 CHAT API: Final response_content: {response_content[:200]}...")
            print(f"🔍 CHAT API: Final response_content type: {type(response_content)}")
            print(f"🔍 CHAT API: Final response_content length: {len(str(response_content))}")

            # 4. Save updated conversation state for context persistence
            try:
                # Remove database from context before saving (can't serialize)
                if "database" in result["context"]:
                    del result["context"]["database"]
                
                # Convert ChatCompletionMessage objects to serializable format
                serializable_result = _make_serializable(result)
                
                print(f"🔍 DEBUG: Saving conversation state with data: {serializable_result.get('data', {})}")
                print(f"🔍 DEBUG: Session ID: {session_id}, User ID: {current_user.user_id}")
                print(f"🔍 DEBUG: Full serializable_result keys: {list(serializable_result.keys())}")
                
                # Save conversation state to session using the same session_id as retrieval
                await session_manager.store_chat_session(
                    session_id,  # Use the same session_id as retrieval
                    str(current_user.user_id),
                    {"conversation_state": serializable_result}
                )
                print(f"🔍 DEBUG: Conversation state saved successfully")
                print(f"🔄 CHAT API: Saved conversation state with {len(serializable_result.get('messages', []))} messages")
            except Exception as save_error:
                print(f"⚠️ CHAT API: Failed to save conversation state: {save_error}")
                # Don't fail the request if saving fails

            # TODO: ERROR HANDLING - Check if response indicates an error
            is_error = any(error_indicator in response_content for error_indicator in [
                "❌ No employee found",
                "❌ Invalid file data", 
                "❌ User context not available",
                "❌ Error",
                "Failed to",
                "Recursion limit"
            ])
            
            # 5. Return JSON response with "Milo" as agent name
            # Safe data extraction with fallbacks
            agent_response_times = {}
            if isinstance(result, dict) and "agent_response_times" in result:
                agent_response_times = result["agent_response_times"] or {}

            result_status = "completed"
            if isinstance(result, dict) and "status" in result:
                result_status = result["status"] or "completed"

            print(f"🔍 CHAT API: Final ChatResponse being returned:")
            print(f"🔍 CHAT API: - response length: {len(str(response_content))}")
            print(f"🔍 CHAT API: - response preview: {response_content[:200]}...")
            print(f"🔍 CHAT API: - response type: {type(response_content)}")
            print(f"🔍 CHAT API: - success: {not is_error}")
            
            final_response = ChatResponse(
                response=response_content,
                agent="Milo",
                success=not is_error,  # TODO: ERROR HANDLING - Set success based on error detection
                timestamp=datetime.now().isoformat(),
                session_id=current_user.session_id,
                workflow_id=f"workflow_{datetime.now().timestamp()}",
                data={
                    "processing_time": agent_response_times,
                    "status": result_status
                }
            )
            
            print(f"🔍 CHAT API: ChatResponse object created successfully")
            return final_response

    except Exception as e:
        
        traceback.print_exc()
        print(f"❌ Chat processing failed: {str(e)}")
        
        # Return error response in expected format
        return ChatResponse(
            response=f"I encountered an error processing your request: {str(e)}",
            agent="error_handler",
            success=False,
            timestamp=datetime.now().isoformat(),
            session_id="error-session",
            data={"error": str(e)}
        )
    finally:
        print("Do not close the db session")

@router.post("/message/stream")
async def send_chat_message_stream(
    chat_request: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_ai_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Sends a message to the new agentic graph and streams the response.
    """
    try:
        message_content = chat_request.message
        if not message_content:
            raise HTTPException(status_code=400, detail="Message content is required.")

        # --- LangGraph Invocation ---
        initial_message = HumanMessage(content=message_content)
        initial_state = create_initial_state(
            user_id=str(current_user.user_id),
            session_id=current_user.session_id,
            user_name=current_user.user.full_name or current_user.user.email,
            user_role=current_user.role,
            initial_message=initial_message
        )

        # Add database to context (removed to avoid unhashable type error)
        #initial_state["context"]["database"] = db

        # Convert messages to serializable format before invoking agent
        if initial_state.get("messages"):
            serializable_messages = []
            for msg in initial_state["messages"]:
                if hasattr(msg, 'type') and hasattr(msg, 'content'):
                    # LangChain message object
                    serializable_messages.append({
                        "type": msg.type,
                        "content": msg.content,
                        "role": getattr(msg, 'role', msg.type)
                    })
                elif isinstance(msg, dict):
                    # Already a dict
                    serializable_messages.append(msg)
                else:
                    # Fallback - convert to string
                    serializable_messages.append({
                        "type": "unknown",
                        "content": str(msg),
                        "role": "unknown"
                    })
            initial_state["messages"] = serializable_messages

        # Ensure all state values are hashable/serializable
        initial_state = _make_serializable_state(initial_state)

        # DEBUG: Add additional validation before LangGraph invocation
        try:
            # Validate that all state values are hashable
            _validate_state_hashable(initial_state)
            print("✅ Stream state validation passed - all values are hashable")
        except Exception as validation_error:
            print(f"❌ Stream state validation failed: {validation_error}")
            # Continue anyway, but log the issue

        # 🚀 PHASE 2 OPTIMIZATION: Reduced recursion limit for streaming responses
        # TODO: If streaming responses become incomplete, revert recursion_limit to 10
        async def stream_generator():
            async for event in agent_app.astream(initial_state, config={"recursion_limit": 4}):
                yield f"data: {json.dumps(event)}"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for the chat system"""
    try:
        return {
            "status": "healthy",
            "agents": "operational",
            "graph": "compiled",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/agents")
async def get_agents():
    """Get available agents and their capabilities"""
    return {
        "agents": {
            "client_agent": {
                "name": "Client Agent",
                "description": "Manages client information, onboarding, and relationships",
                "capabilities": ["create_client", "update_client", "search_clients", "get_client_details"]
            },
            "contract_agent": {
                "name": "Contract Agent", 
                "description": "Handles contract creation, management, and tracking",
                "capabilities": ["create_contract", "update_contract", "search_contracts", "get_contract_details"]
            },
            "employee_agent": {
                "name": "Employee Agent",
                "description": "Manages employee information and HR operations",
                "capabilities": ["create_employee", "update_employee", "search_employees", "get_employee_details"]
            },
            "deliverable_agent": {
                "name": "Deliverable Agent",
                "description": "Tracks project deliverables and milestones",
                "capabilities": ["create_deliverable", "update_deliverable", "search_deliverables", "track_progress"]
            },
            "time_agent": {
                "name": "Time Tracking Agent",
                "description": "Manages time entries and productivity tracking",
                "capabilities": ["log_time", "update_time_entry", "generate_reports", "track_productivity"]
            },
            "user_agent": {
                "name": "User Agent",
                "description": "Handles user management and authentication",
                "capabilities": ["manage_users", "update_profiles", "handle_permissions", "user_analytics"]
            }
        },
        "graph_status": "operational",
        "total_agents": 6
    }
