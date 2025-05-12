import json
import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
private_key = os.getenv("PRIVATE_KEY")

if not private_key:
    raise ValueError("Private key not found! Please check your .env file.")

# Load transaction details from JSON
with open("transaction_data.json", "r") as file:
    data = json.load(file)

# Connect to Polygon RPC endpoint
rpc_url = "https://polygon-rpc.com"
web3 = Web3(Web3.HTTPProvider(rpc_url))

# Ensure connection success
assert web3.is_connected(), "Failed to connect to Polygon blockchain"

# Addresses
sender_address = web3.eth.account.from_key(private_key).address
contract_address = "0x0B00a466AD7e747D28F599c8ecd701EEC4C2E99f"

# Load contract ABI
contract_abi = [
    {
        "constant": False,
        "inputs": [
            {"name": "eventId", "type": "string"},
            {"name": "message", "type": "string"},
            {"name": "tokens", "type": "tuple[]"},
            {"name": "internalTransfer", "type": "tuple"}
        ],
        "name": "emitEventWithTransfers",
        "outputs": [],
        "type": "function"
    }
]
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Loop through districts
for district in data["districts"]:
    print(f"Processing District ID: {district['districtId']}")

    # Extract token transfers
    tokens_to_transfer = [
        (token, details["amount"], details["receiver"], details["contract"])
        for token, details in district["tokens"].items()
    ]

    # Extract POL transfer
    internal_transfer = (
        "POL",
        district["internalTransfers"]["POL"]["amount"],
        district["internalTransfers"]["POL"]["sender"],
        district["internalTransfers"]["POL"]["receiver"]
    )

    # Build transaction
    tx = contract.functions.emitEventWithTransfers(
        district["researchType"],  # eventId
        json.dumps(district),  # message
        tokens_to_transfer,  # ERC-20 token transfers
        internal_transfer  # POL transfer
    ).build_transaction({
        "from": sender_address,
        "gas": 1000000,
        "gasPrice": web3.to_wei("612.94176276", "gwei"),
        "nonce": web3.eth.get_transaction_count(sender_address)
    })

    # **Sign and send transaction**
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    print(f"Transaction sent for District {district['districtId']}: {tx_hash.hex()}")

print("All transactions executed successfully!")
