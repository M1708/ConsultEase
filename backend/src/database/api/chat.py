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
from src.aiagents.graph.graph import app as agent_app
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

def _make_serializable(obj):
    """Convert OpenAI objects to JSON-serializable format"""
    if hasattr(obj, 'model_dump'):
        # Pydantic models
        return obj.model_dump()
    elif hasattr(obj, '__dict__'):
        # OpenAI ChatCompletionMessage objects
        if hasattr(obj, 'content') and hasattr(obj, 'role'):
            return {
                'role': obj.role,
                'content': obj.content,
                'tool_calls': getattr(obj, 'tool_calls', None)
            }
        else:
            # Generic object with __dict__
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):  # Skip private attributes
                    result[key] = _make_serializable(value)
            return result
    elif isinstance(obj, dict):
        return {key: _make_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Fallback to string representation
        return str(obj)

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
        async with get_ai_db() as auth_db:
            current_user = await get_current_user(credentials, auth_db)
        
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
                existing_state = await session_manager.get_session(session_id, user_id)
                print(f"🔄 CHAT API: Found existing state for session {session_id}")
            except Exception as e:
                print(f"🔄 CHAT API: No existing state found, creating new: {e}")
            
            # Create or update state
            if existing_state:
                # Add new message to existing conversation
                new_message = HumanMessage(content=message_content)
                existing_state["messages"].append(new_message)
                
                # Update context
                existing_state["context"]["last_interaction"] = datetime.now().isoformat()
                existing_state["context"]["interaction_count"] += 1
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
                if hasattr(last_message, 'content'):
                    response_text = last_message.content
                else:
                    response_text = str(last_message)
                
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
                await session_manager.save_session(session_id, result)
                print(f"💾 CHAT API: Saved session {session_id}")
            except Exception as e:
                print(f"⚠️ CHAT API: Failed to save session: {e}")
            
            # TODO: ERROR HANDLING - Return success: false for errors to trigger frontend clearing
            return {
                "response": response_text,
                "agent": agent_name,
                "success": not is_error,  # TODO: ERROR HANDLING - Set success based on error detection
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "workflow_id": result.get("workflow_id"),
                "data": result.get("data", {})
            }
            
    except Exception as e:
        print(f"❌ Chat processing with file failed: {str(e)}")
        return {
            "response": f"I encountered an error processing your request with file: {str(e)}",
            "agent": "error_handler",
            "success": False,
            "status": "chat_with_file_error",
            "error": str(e)
        }

@router.post("/message")
async def send_chat_message(chat_request: ChatRequest, request: Request):
    """
    Sends a message to the new agentic graph and returns a JSON response.
    """
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

            # --- LangGraph Invocation for complex messages ---
            # 1. Load existing conversation context or create new one
            
            session_manager = SessionManager()
            user_id = str(current_user.user_id)
            session_id = chat_request.session_id or current_user.session_id
            
            # Try to load existing conversation state
            existing_state = None
            try:
                chat_session_data = await session_manager.get_chat_session(
                    session_id, 
                    user_id
                )
                if chat_session_data and "conversation_state" in chat_session_data:
                    existing_state = chat_session_data["conversation_state"]
                    print(f"🔄 CHAT API: Loaded existing conversation state with {len(existing_state.get('messages', []))} messages")
            except Exception as e:
                print(f"🔄 CHAT API: No existing state found, creating new: {e}")
            
            # Create or update state
            if existing_state:
                # Add new message to existing conversation
                new_message = HumanMessage(content=message_content)
                existing_state["messages"].append(new_message)
                
                # Update context
                existing_state["context"]["last_interaction"] = datetime.now().isoformat()
                existing_state["context"]["interaction_count"] += 1
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
                
                # Add database to context
                #initial_state["context"]["database"] = db
                print(f"🔄 CHAT API: Created new conversation state")
            
            # Add file_info to context if provided
            if hasattr(chat_request, 'file_info') and chat_request.file_info:
                initial_state["context"]["file_info"] = chat_request.file_info

            # 🚀 PHASE 2 OPTIMIZATION: Reduced recursion limit to prevent multiple iterations
            # TODO: If agent responses become incomplete or tools don't execute properly, revert recursion_limit to 10
            print(f"🔍 DEBUG: Invoking agent with recursion_limit=20")
            print(f"🔍 DEBUG: Initial state keys: {list(initial_state.keys())}")
            print(f"🔍 DEBUG: Context keys: {list(initial_state.get('context', {}).keys())}")
            result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 20})
            print(f"🔍 DEBUG: Agent invocation completed")
            
            # 3. Extract the response from the result
            response_content = "I'm processing your request..."
            
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    response_content = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    response_content = last_message['content']

            # 4. Save updated conversation state for context persistence
            try:
                # Remove database from context before saving (can't serialize)
                if "database" in result["context"]:
                    del result["context"]["database"]
                
                # Convert ChatCompletionMessage objects to serializable format
                serializable_result = _make_serializable(result)
                
                # Save conversation state to session
                await session_manager.store_chat_session(
                    current_user.session_id,
                    str(current_user.user_id),
                    {"conversation_state": serializable_result}
                )
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
            return ChatResponse(
                response=response_content,
                agent="Milo",
                success=not is_error,  # TODO: ERROR HANDLING - Set success based on error detection
                timestamp=datetime.now().isoformat(),
                session_id=current_user.session_id,
                workflow_id=f"workflow_{datetime.now().timestamp()}",
                data={
                    "processing_time": result.get("agent_response_times", {}),
                    "status": result.get("status", "completed")
                }
            )

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
        
        # Add database to context
        #initial_state["context"]["database"] = db

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
