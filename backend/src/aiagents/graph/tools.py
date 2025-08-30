
import json
from typing import Dict, Any, List

from src.aiagents.graph.state import AgentState

# --- Import all tool functions and params from the existing tool files ---
from src.aiagents.tools.contract_tools import (
    create_client_tool, search_clients_tool, get_all_clients_tool, get_client_details_tool,
    get_contract_details_tool, analyze_contract_tool, smart_create_contract_tool,
    smart_contract_document_tool, get_contracts_by_client_tool, get_all_contracts_tool,
    get_all_clients_with_contracts_tool, get_contracts_by_billing_date_tool, update_contract_tool, 
    search_contracts_tool,
    CreateClientParams, SmartContractParams, ContractDocumentParams, UpdateContractParams, SearchContractsParams, ContractToolResult
)
from  src.aiagents.tools.client_tools import (
    update_client_tool as update_client_tool_client, UpdateClientParams as UpdateClientParamsClient, ClientToolResult
)
# ... import other tools for other agents as they are integrated

# --- Tool Wrappers (migrated from ContractAgent) ---
# These wrappers handle the messy work of unpacking arguments and calling the core tool function.

def _create_client_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = CreateClientParams(**kwargs)
    result = create_client_tool(params, context, db)
    return result.model_dump()

def _get_all_clients_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    result = get_all_clients_tool(db)
    return result.model_dump()

def _get_contract_details_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    contract_id = kwargs.get("contract_id")
    client_name = kwargs.get("client_name")
    result = get_contract_details_tool(contract_id, client_name, db)
    return result.model_dump()

def _get_client_details_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    client_name = kwargs.get("client_name")
    result = get_client_details_tool(client_name, db)
    # ClientToolResult is not a Pydantic model, so convert manually
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

def _search_clients_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    search_term = kwargs.get("search_term")
    limit = kwargs.get("limit", 10)
    result = search_clients_tool(search_term, limit, db)
    return result.model_dump()

def _analyze_contract_wrapper(**kwargs) -> Dict[str, Any]:
    contract_text = kwargs.get("contract_text")
    result = analyze_contract_tool(contract_text)
    return result.model_dump()

def _smart_create_contract_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = SmartContractParams(**kwargs)
    result = smart_create_contract_tool(params, context, db)
    return result.model_dump()

def _get_contracts_by_client_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    client_name = kwargs.get("client_name")
    result = get_contracts_by_client_tool(client_name, db)
    return result.model_dump()

def _get_all_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    result = get_all_contracts_tool(db)
    return result.model_dump()

def _get_contracts_by_billing_date_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    result = get_contracts_by_billing_date_tool(start_date, end_date, db)
    return result.model_dump()

def _update_contract_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateContractParams(**kwargs)
    result = update_contract_tool(params, context, db)
    return result.model_dump()

def _update_client_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = UpdateClientParamsClient(**kwargs)
    result = update_client_tool_client(params, context, db)
    # ClientToolResult is not a Pydantic model, so convert manually
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data
    }

def _smart_contract_document_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    params = ContractDocumentParams(**kwargs)
    result = smart_contract_document_tool(params, db)
    return result.model_dump()

def _get_all_clients_with_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    db = kwargs.pop('db', None)
    result = get_all_clients_with_contracts_tool(db)
    return result.model_dump()

def _create_client_and_contract_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for creating a client and then a contract in sequence"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    
    try:
        # First create the client
        client_params = CreateClientParams(
            client_name=kwargs.get('client_name'),
            primary_contact_name=kwargs.get('primary_contact_name'),
            primary_contact_email=kwargs.get('primary_contact_email'),
            industry=kwargs.get('industry', 'Startup')
        )
        
        client_result = create_client_tool(client_params, context, db)
        if not client_result.success:
            return client_result.model_dump()
        
        # Then create the contract
        contract_params = SmartContractParams(
            client_name=kwargs.get('client_name'),
            contract_type=kwargs.get('contract_type', 'Fixed'),
            original_amount=kwargs.get('original_amount'),
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
            billing_frequency='Monthly',
            billing_prompt_next_date=kwargs.get('billing_prompt_next_date')
        )
        
        contract_result = smart_create_contract_tool(contract_params, context, db)
        
        # Combine results
        if contract_result.success:
            return {
                "success": True,
                "message": f"✅ Successfully created client '{kwargs.get('client_name')}' and contract. Client ID: {client_result.data.get('client_id')}, Contract ID: {contract_result.data.get('contract_id')}",
                "data": {
                    "client": client_result.data,
                    "contract": contract_result.data
                }
            }
        else:
            return contract_result.model_dump()
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to create client and contract: {str(e)}"
        }

def _update_contract_by_id_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for updating contract by ID instead of client name"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    contract_id = kwargs.get('contract_id')
    
    try:
        if db is None:
            from src.database.core.database import get_db
            db = next(get_db())
        
        # Find the contract by ID
        from src.database.core.models import Contract, Client
        contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
        
        if not contract:
            return {
                "success": False,
                "message": f"❌ Contract with ID {contract_id} not found."
            }
        
        # Get the client name
        client = db.query(Client).filter(Client.client_id == contract.client_id).first()
        if not client:
            return {
                "success": False,
                "message": f"❌ Client for contract ID {contract_id} not found."
            }
        
        # Use the existing update_contract_tool with client name
        params = UpdateContractParams(
            client_name=client.client_name,
            contract_id=contract_id,
            billing_prompt_next_date=kwargs.get('billing_prompt_next_date'),
            status=kwargs.get('status'),
            notes=kwargs.get('notes')
        )
        
        result = update_contract_tool(params, context, db)
        return result.model_dump()
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to update contract by ID: {str(e)}"
        }

def _search_contracts_wrapper(**kwargs) -> Dict[str, Any]:
    """Wrapper for searching contracts by various criteria"""
    db = kwargs.pop('db', None)
    context = kwargs.pop('context', None)
    params = SearchContractsParams(**kwargs)
    result = search_contracts_tool(params, db)
    return result.model_dump()

# --- Central Tool Registry ---
TOOL_REGISTRY = {
    "create_client": _create_client_wrapper,
    "search_clients": _search_clients_wrapper,
    "get_all_clients": _get_all_clients_wrapper,
    "get_all_clients_with_contracts": _get_all_clients_with_contracts_wrapper,
    "get_client_details": _get_client_details_wrapper,
    "analyze_contract": _analyze_contract_wrapper,
    "create_contract": _smart_create_contract_wrapper,
    "get_client_contracts": _get_contracts_by_client_wrapper,
    "get_all_contracts": _get_all_contracts_wrapper,
    "get_contract_details": _get_contract_details_wrapper,
    "get_contracts_by_billing_date": _get_contracts_by_billing_date_wrapper,
    "search_contracts": _search_contracts_wrapper,
    "update_contract": _update_contract_wrapper,
    "update_client": _update_client_wrapper,
    "manage_contract_document": _smart_contract_document_wrapper,
    "create_client_and_contract": _create_client_and_contract_wrapper,
    "update_contract_by_id": _update_contract_by_id_wrapper,
    # Other tools will be registered here
}

def tool_executor_node(state: AgentState) -> Dict:
    """
    Executes tools requested by an agent. This node is the central tool handler for the entire graph.
    It takes tool calls from the last message in the state, executes them, and returns the results.
    """
    last_message = state['messages'][-1]
    tool_calls = getattr(last_message, 'tool_calls', [])
    
    if not tool_calls:
        return {"messages": []}

    # The database session should be in the state's data payload, but context is in state.context
    db_session = state.get('data', {}).get('database')
    context = state.get('context', {})

    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        print(f"🛠️ Tool Executor: Executing tool '{tool_name}'")

        if tool_name not in TOOL_REGISTRY:
            result_content = json.dumps({"error": f"Tool '{tool_name}' not found in registry."})
        else:
            try:
                tool_function = TOOL_REGISTRY[tool_name]
                args = json.loads(tool_call.function.arguments)
                
                # Add the database session and context to the arguments for the wrapper
                args['db'] = db_session
                args['context'] = context
                
                output = tool_function(**args)
                result_content = json.dumps(output)

            except Exception as e:
                import traceback
                traceback.print_exc()
                result_content = json.dumps({"error": str(e), "tool_name": tool_name})
                print(f"🔥 Tool Executor: Error running '{tool_name}': {e}")

        results.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": tool_name,
            "content": result_content,
        })

    return {"messages": results}
