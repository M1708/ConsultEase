import asyncio
from src.database.core.database import get_ai_db
from src.database.core.models import Contract, Client
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def create_second_contract():
    try:
        async with get_ai_db() as session:
            # Find Acme client
            client_result = await session.execute(select(Client).filter(Client.client_name.ilike('%Acme%')))
            client = client_result.scalar_one_or_none()
            
            if not client:
                print('Acme client not found')
                return False
                
            print(f'Found client: {client.client_name} (ID: {client.client_id})')
            
            # Create a second contract
            new_contract = Contract(
                client_id=client.client_id,
                contract_type='Time & Material',
                original_amount=50000.00,
                current_amount=50000.00,
                billing_frequency='Monthly',
                start_date='2024-01-01',
                end_date='2024-12-31',
                status='Active',
                notes='Second contract for testing multiple contracts scenario'
            )
            
            session.add(new_contract)
            await session.commit()
            await session.refresh(new_contract)
            
            print(f'Created second contract with ID: {new_contract.contract_id}')
            
            # Check total contracts for Acme
            contracts_result = await session.execute(select(Contract).options(
                selectinload(Contract.client)
            ).filter(Contract.client_id == client.client_id))
            contracts = contracts_result.scalars().all()
            
            print(f'Total contracts for {client.client_name}: {len(contracts)}')
            for i, contract in enumerate(contracts):
                print(f'  Contract {i+1}: ID {contract.contract_id}, Type: {contract.contract_type}, Amount: ${contract.original_amount}')
            
            return True
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(create_second_contract())
print(f'\nTest result: {result}')
