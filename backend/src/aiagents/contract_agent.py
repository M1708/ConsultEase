from typing import Dict, Any, List

class ContractAgent:
    """
    A container for the Contract Agent's configuration.
    All runtime logic is now handled by the LangGraph engine.
    """
    def __init__(self):
        """Initializes the agent with its specific instructions and tool schemas."""
        self.instructions = "You are Milo, an expert assistant for contract management."
        self.tools = self._get_tool_schemas()

    def get_capabilities(self) -> Dict[str, Any]:
        """
        A simple description of the agent's purpose.
        This might be used by a future monitoring endpoint.
        """
        return {
            "name": "ContractAgent",
            "description": "Client and contract management specialist",
            "tools": [tool['function']['name'] for tool in self.tools]
        }

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Defines the OpenAI function calling schemas for the tools this agent can use.
        This is the primary piece of configuration the agent provides to the graph.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_client",
                    "description": "Create a new client record in the CRM system with company information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The full name of the client company"},
                            "industry": {"type": "string", "description": "The industry the client operates in"},
                            "primary_contact_name": {"type": "string", "description": "Name of the primary contact"},
                            "primary_contact_email": {"type": "string", "description": "Email of the primary contact"},
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_clients",
                    "description": "Search for existing clients by name, industry, or other criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Term to search for clients"}
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_clients",
                    "description": "Get a list of all clients in the system.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_details",
                    "description": "Get detailed information for a specific client (basic client info only).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The name of the client"}
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_client_contracts",
                    "description": "Get all contracts for a specific client. Use this when user asks for contract details, contract information, or anything related to a client's contracts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The name of the client whose contracts to retrieve"}
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_contract_details",
                    "description": "Get detailed information for a specific contract by contract ID or client name. Use this when user asks for 'contract details for contract 108', 'show me contract 108', or similar requests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contract_id": {"type": "integer", "description": "The specific contract ID to get details for"},
                            "client_name": {"type": "string", "description": "The name of the client (alternative to contract_id)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_contracts",
                    "description": "Get all contracts across all clients. Use this when user asks to 'show all contracts', 'list all contracts', or similar requests that need all contract information without specifying a client.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_clients_with_contracts",
                    "description": "Get a comprehensive list of all clients with their contract details. Use this when user asks for 'clients with contracts', 'clients and their contracts', or similar requests that need both client and contract information.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_contract",
                    "description": "Create a new contract for a client.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Name of the client for the contract"},
                            "contract_type": {"type": "string", "description": "Type of contract: Fixed, Hourly, or Retainer"},
                            "original_amount": {"type": "number", "description": "The total amount of the contract"},
                            "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                            "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"}
                        },
                        "required": ["client_name", "contract_type", "original_amount", "start_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_contract",
                    "description": "Update an existing contract for a client. Use this to modify contract details like billing dates, amounts, status, etc. If client has multiple contracts, will ask user to specify contract ID or say 'all' to update all contracts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Name of the client whose contract to update"},
                            "contract_id": {"type": "integer", "description": "Specific contract ID to update (optional - will use most recent if not provided)"},
                            "user_response": {"type": "string", "description": "User's response to contract selection prompt (e.g., '1', '2', '108', 'Contract 108', 'all', 'for both')"},
                            "update_all": {"type": "boolean", "description": "Whether to update all contracts for the client (set to true when user says 'all', 'both', 'for all', etc.)"},
                            "start_date": {"type": "string", "description": "New start date in YYYY-MM-DD format"},
                            "end_date": {"type": "string", "description": "New end date in YYYY-MM-DD format"},
                            "contract_type": {"type": "string", "description": "New contract type: Fixed, Hourly, or Retainer"},
                            "original_amount": {"type": "number", "description": "New original amount"},
                            "billing_frequency": {"type": "string", "description": "New billing frequency: Monthly, Weekly, One-time"},
                            "billing_prompt_next_date": {"type": "string", "description": "New billing prompt date in YYYY-MM-DD format"},
                            "status": {"type": "string", "description": "New contract status"},
                            "notes": {"type": "string", "description": "New or updated notes"}
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_client_and_contract",
                    "description": "Create a new client and contract in one operation. Use this when the user wants to create a contract for a new client that doesn't exist yet. The user message should contain both client details (name, contact info) and contract details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The full name of the new client company"},
                            "primary_contact_name": {"type": "string", "description": "Name of the primary contact person"},
                            "primary_contact_email": {"type": "string", "description": "Email of the primary contact person"},
                            "industry": {"type": "string", "description": "The industry the client operates in (e.g., Startup, Technology, Manufacturing)"},
                            "contract_type": {"type": "string", "description": "Type of contract: Fixed, Hourly, or Retainer"},
                            "original_amount": {"type": "number", "description": "The total amount of the contract"},
                            "start_date": {"type": "string", "description": "Contract start date in YYYY-MM-DD format"},
                            "end_date": {"type": "string", "description": "Contract end date in YYYY-MM-DD format"},
                            "billing_prompt_next_date": {"type": "string", "description": "Next billing prompt date in YYYY-MM-DD format"},
                            "file_data": {"type": "string", "description": "Base64 encoded file content for contract document (optional)"},
                            "filename": {"type": "string", "description": "Original filename for contract document (optional)"},
                            "file_size": {"type": "integer", "description": "File size in bytes for contract document (optional)"},
                            "mime_type": {"type": "string", "description": "MIME type of the contract document file (optional)"}
                        },
                        "required": ["client_name", "contract_type", "original_amount", "start_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_contract_by_id",
                    "description": "Update a contract by its specific contract ID. Use this when the user provides a contract ID directly (e.g., 'contract id 84', 'contract 84').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contract_id": {"type": "integer", "description": "The specific contract ID to update"},
                            "start_date": {"type": "string", "description": "New start date in YYYY-MM-DD format"},
                            "end_date": {"type": "string", "description": "New end date in YYYY-MM-DD format"},
                            "contract_type": {"type": "string", "description": "New contract type: Fixed, Hourly, or Retainer"},
                            "original_amount": {"type": "number", "description": "New original amount"},
                            "billing_frequency": {"type": "string", "description": "New billing frequency: Monthly, Weekly, One-time"},
                            "billing_prompt_next_date": {"type": "string", "description": "New billing prompt date in YYYY-MM-DD format"},
                            "status": {"type": "string", "description": "New contract status"},
                            "notes": {"type": "string", "description": "New or updated notes"}
                        },
                        "required": ["contract_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_contracts",
                    "description": "Search and filter contracts by various criteria such as billing frequency, contract type, status, client name, or amount range. Use this when user asks for contracts with specific characteristics like 'monthly billing', 'fixed contracts', 'active contracts', etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "billing_frequency": {"type": "string", "description": "Filter by billing frequency: Monthly, Weekly, One-time"},
                            "contract_type": {"type": "string", "description": "Filter by contract type: Fixed, Hourly, Retainer"},
                            "status": {"type": "string", "description": "Filter by contract status: active, draft, completed, terminated"},
                            "client_name": {"type": "string", "description": "Filter by client name (partial match)"},
                            "min_amount": {"type": "number", "description": "Minimum contract amount"},
                            "max_amount": {"type": "number", "description": "Maximum contract amount"},
                            "start_date_from": {"type": "string", "description": "Filter contracts starting from this date (YYYY-MM-DD)"},
                            "start_date_to": {"type": "string", "description": "Filter contracts starting before this date (YYYY-MM-DD)"},
                            # TODO: If contract search becomes slow or unreliable, revert these new search parameters
                            "billing_date_next_month": {"type": "boolean", "description": "Filter contracts with billing dates in the next month"},
                            "billing_date_is_null": {"type": "boolean", "description": "Filter contracts with no billing date set"}
                        },
                        "required": []
                    }
                }
            },
            # 🔧 NEW TOOL: Added for filtering contracts by next month billing dates
            # TODO: If this change doesn't fix the issue, remove this tool definition
            {
                "type": "function",
                "function": {
                    "name": "get_contracts_for_next_month_billing",
                    "description": "Get contracts with billing prompt dates in the next month or later in the current month. Use this when user asks for 'contracts with billing dates next month', 'contracts due for billing next month', 'upcoming billing prompt date', 'contracts with upcoming billing', or similar requests.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "upload_contract_document",
                    "description": "Upload a document for a client's contract. Handles file upload and database updates. If client has multiple contracts, will ask user to specify contract ID. CRITICAL: Always extract client name from user message - look for patterns like 'for client [Name]', 'for [Name]', 'this is for [Name]'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Client name extracted from user message (e.g., 'Acme Corp' from 'for client Acme Corp'). REQUIRED when contract_id not provided."},
                            "contract_id": {"type": "integer", "description": "Specific contract ID (optional - will use latest contract if not provided)"},
                            "file_data": {"type": "string", "description": "Base64 encoded file content"},
                            "filename": {"type": "string", "description": "Original filename"},
                            "file_size": {"type": "integer", "description": "File size in bytes"},
                            "mime_type": {"type": "string", "description": "MIME type of the file"}
                        },
                        "required": ["client_name", "file_data", "filename", "file_size", "mime_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_contract_document",
                    "description": "Get information about contract documents for a client. Use this to check if a contract has documents or to get document details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Name of the client"},
                            "contract_id": {"type": "integer", "description": "Specific contract ID (optional)"},
                            "document_action": {"type": "string", "description": "Action to perform: 'info', 'check', 'details'"}
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_contract_document",
                    "description": "Delete contract document(s) for a client. Can delete all documents for a client or specific contract document.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Name of the client"},
                            "contract_id": {"type": "integer", "description": "Specific contract ID (optional - will delete all contract documents if not provided)"}
                        },
                        "required": ["client_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_contract",
                    "description": "Delete a contract for a client. If client has multiple contracts, will ask user to specify contract ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "Name of the client"},
                            "contract_id": {"type": "integer", "description": "Specific contract ID (optional - will ask for clarification if multiple contracts exist)"},
                            "delete_all": {"type": "boolean", "description": "Set to true to delete all contracts for the client (use when user says 'all')"},
                            "user_response": {"type": "string", "description": "User's response to contract selection prompt (e.g., '1', '2', 'all')"}
                        },
                        "required": ["client_name"]
                    }
                }
            }
        ]
