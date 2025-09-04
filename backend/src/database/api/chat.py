from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.database.core.database import get_db
from datetime import datetime
from src.auth.dependencies import get_current_user, AuthenticatedUser
import json
import re
from fastapi.security import HTTPAuthorizationCredentials

# --- New Imports for LangGraph Integration ---
from src.aiagents.graph.graph import app as agent_app
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from src.aiagents.graph.state import create_initial_state

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

class ChatResponse(BaseModel):
    response: str
    agent: str
    success: bool
    timestamp: str
    session_id: str
    workflow_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@router.post("/greeting")
async def fast_greeting(request: Request):
    """
    Ultra-fast greeting endpoint with optional user personalization.
    """
    import time
    start_time = time.perf_counter()
    
    try:
        print(f"🚀 FAST GREETING ENDPOINT: Request received at {datetime.now()}")
        
        body = await request.json()
        message_content = body.get("message", "")
        
        # Try to get user name for personalization (optional, don't fail if not available)
        greeting_response = "Hello! How can I help you today?"
        session_id = "fast-greeting"
        
        try:
            # Optional: Try to get user info if auth token is provided
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                
                token = auth_header.split(" ")[1]
                credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                
                db_gen = get_db()
                db = next(db_gen)
                
                current_user = await get_current_user(credentials, db)
                
                # Extract first name for personalized greeting
                user_name = current_user.user.full_name or current_user.user.email
                first_name = user_name.split()[0] if user_name else ''
                
                if first_name:
                    greeting_response = f"Hello {first_name}! How can I help you today?"
                
                session_id = current_user.session_id
                print(f"⚡ FAST GREETING: Personalized for {first_name}")
                
        except Exception as auth_error:
            # If auth fails, just use generic greeting (don't fail the whole request)
            print(f"⚡ FAST GREETING: Auth failed, using generic greeting: {auth_error}")
        
        # Return instant greeting response
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
        print(f"✅ FAST GREETING ENDPOINT: Completed in {(end_time - start_time) * 1000:.2f}ms")
        
        return response
        
    except Exception as e:
        end_time = time.perf_counter()
        print(f"❌ Fast greeting failed after {(end_time - start_time) * 1000:.2f}ms: {e}")
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
async def fast_clients(request: Request):
    """
    Ultra-fast client listing endpoint that bypasses LangGraph for simple queries.
    """
    import time
    start_time = time.perf_counter()
    
    try:
        print(f"🚀 FAST CLIENTS ENDPOINT: Request received at {datetime.now()}")
        
        body = await request.json()
        message_content = body.get("message", "")
        
        # Get dependencies for client data access
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            
            current_user = await get_current_user(credentials, db)
        except Exception as e:
            print(f"❌ Auth failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get all clients directly from database
        from src.database.core.models import Client
        clients = db.query(Client).order_by(Client.client_name).all()
        
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
        
        # Format response message with detailed information
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
        
        # Close database session
        db.close()
        
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
        
        print(f"✅ FAST CLIENTS ENDPOINT: Completed in {processing_time:.2f}ms")
        
        return response
        
    except Exception as e:
        end_time = time.perf_counter()
        print(f"❌ Fast clients failed after {(end_time - start_time) * 1000:.2f}ms: {e}")
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

@router.post("/message")
async def send_chat_message(request: Request):
    """
    Sends a message to the new agentic graph and returns a JSON response.
    """
    db = next(get_db())
    try:
        body = await request.json()
        message_content = body.get("message")
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
            print(f"🔥 CHAT API: ULTRA-FAST GREETING PATH!")
            # Try to get personalized greeting with auth
            try:
                print("Inside try block of ultra-fast greeting")
                
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                    
                    current_user = await get_current_user(credentials, db)
                    
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
                    if not first_name:
                        user_name = f"{current_user.user.first_name} {current_user.user.last_name}" if current_user.user.first_name and current_user.user.last_name else current_user.user.first_name or current_user.user.last_name or current_user.user.email
                        first_name = user_name.split()[0] if user_name else ''
                    
                    if first_name:
                        greeting_response = f"Hello {first_name}! How can I help you today?"
                        session_id = current_user.session_id
                        print(f"🔥 CHAT API: Personalized greeting for {first_name}")
                        
                        return ChatResponse(
                            response=greeting_response,
                            agent="Milo",
                            success=True,
                            timestamp=datetime.now().isoformat(),
                            session_id=session_id,
                            workflow_id=f"workflow_{datetime.now().timestamp()}",
                            data={
                                "processing_time": {"greeting": "< 0.1s"},
                                "status": "ultra_fast_greeting_personalized"
                            }
                        )
            except Exception as auth_error:
                print(f"🔥 CHAT API: Auth failed for greeting, using generic: {auth_error}")
            
            # Fallback to generic greeting
            return ChatResponse(
                response="Hello! How can I help you today?",
                agent="Milo",
                success=True,
                timestamp=datetime.now().isoformat(),
                session_id="fast-greeting",
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
        
        # For non-fast-path messages, get dependencies and proceed normally
        print(f"🔥 CHAT API: Getting dependencies for complex query...")
        
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            
            current_user = await get_current_user(credentials, db)
        except Exception as e:
            print(f"❌ Auth failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        print(f"🔥 CHAT API: Dependencies loaded, proceeding with LangGraph...")

        # --- LangGraph Invocation for complex messages ---
        # 1. Load existing conversation context or create new one
        from src.auth.session_manager import SessionManager
        session_manager = SessionManager()
        
        # Try to load existing conversation state
        existing_state = None
        try:
            chat_session_data = await session_manager.get_chat_session(
                current_user.session_id, 
                str(current_user.user_id)
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
            existing_state["context"]["database"] = db
            
            initial_state = existing_state
            print(f"🔄 CHAT API: Updated existing state, now has {len(initial_state['messages'])} messages")
        else:
            # Create new conversation state
            initial_message = HumanMessage(content=message_content)
            user_full_name = f"{current_user.user.first_name} {current_user.user.last_name}" if current_user.user.first_name and current_user.user.last_name else current_user.user.first_name or current_user.user.last_name or current_user.user.email
            initial_state = create_initial_state(
                user_id=str(current_user.user_id),
                session_id=current_user.session_id,
                user_name=user_full_name,
                user_role=current_user.role,
                initial_message=initial_message
            )
            
            # Add database to context
            initial_state["context"]["database"] = db
            print(f"🔄 CHAT API: Created new conversation state")

        # 🚀 PHASE 2 OPTIMIZATION: Reduced recursion limit to prevent multiple iterations
        # TODO: If agent responses become incomplete or tools don't execute properly, revert recursion_limit to 10
        result = await agent_app.ainvoke(initial_state, config={"recursion_limit": 10})
        
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

        # 5. Return JSON response with "Milo" as agent name
        return ChatResponse(
            response=response_content,
            agent="Milo",
            success=True,
            timestamp=datetime.now().isoformat(),
            session_id=current_user.session_id,
            workflow_id=f"workflow_{datetime.now().timestamp()}",
            data={
                "processing_time": result.get("agent_response_times", {}),
                "status": result.get("status", "completed")
            }
        )

    except Exception as e:
        import traceback
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
        db.close()

@router.post("/message/stream")
async def send_chat_message_stream(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Sends a message to the new agentic graph and streams the response.
    """
    try:
        body = await request.json()
        message_content = body.get("message")
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
        initial_state["context"]["database"] = db

        # 🚀 PHASE 2 OPTIMIZATION: Reduced recursion limit for streaming responses
        # TODO: If streaming responses become incomplete, revert recursion_limit to 10
        async def stream_generator():
            async for event in agent_app.astream(initial_state, config={"recursion_limit": 4}):
                yield f"data: {json.dumps(event)}"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        import traceback
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
