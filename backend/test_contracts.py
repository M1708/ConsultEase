import asyncio
from src.aiagents.tools.contract_tools import get_contracts_by_client_tool

async def check_acme_contracts():
    try:
        result = await get_contracts_by_client_tool("Acme")
        print(f"Contract details result: {result.success}")
        print(f"Message: {result.message}")
        if result.data and "contracts" in result.data:
            contracts = result.data["contracts"]
            print(f"Number of contracts: {len(contracts)}")
            for i, contract in enumerate(contracts):
                contract_id = contract.get("contract_id")
                contract_type = contract.get("contract_type")
                original_amount = contract.get("original_amount")
                print(f"Contract {i+1}: ID {contract_id}, Type: {contract_type}, Amount: ${original_amount}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

result = asyncio.run(check_acme_contracts())
