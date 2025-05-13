import json
import os
import logging
from web3 import Web3
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables from .env file
load_dotenv()
private_key = os.getenv("PRIVATE_KEY")
if not private_key:
    logging.error("Private key not found! Please check your .env file.")
    raise ValueError("Private key not found! Please check your .env file.")
else:
    logging.info("Private key successfully loaded.")

# Load transaction details from JSON file
try:
    with open("transaction_data.json", "r") as file:
        data = json.load(file)
    logging.info("Transaction data loaded from JSON.")
except Exception as e:
    logging.error("Failed to load JSON file: %s", e)
    raise

# Connect to Polygon RPC endpoint
rpc_url = "https://polygon-rpc.com"
web3 = Web3(Web3.HTTPProvider(rpc_url))
if not web3.is_connected():
    logging.error("Failed to connect to Polygon blockchain.")
    raise ConnectionError("Failed to connect to Polygon blockchain")
logging.info("Connected to Polygon blockchain.")

# Get sender address from private key
sender_address = web3.eth.account.from_key(private_key).address
logging.info(f"Sender address: {sender_address}")

# Set and convert the target contract address to a checksum address
contract_address = web3.to_checksum_address("0x0B00a466AD7e747D28F599c8ecd701EEC4C2E99f")

# Updated ABI with proper tuple component definitions and marked as payable.
contract_abi = [
    {
        "constant": False,
        "inputs": [
            {"name": "eventId", "type": "string"},
            {"name": "message", "type": "string"},
            {"name": "tokens", "type": "tuple[]", "components": [
                {"name": "tokenId", "type": "string"},
                {"name": "amount", "type": "uint256"},
                {"name": "receiver", "type": "address"},
                {"name": "tokenContract", "type": "address"}
            ]},
            {"name": "internalTransfer", "type": "tuple", "components": [
                {"name": "tokenId", "type": "string"},
                {"name": "amount", "type": "uint256"},
                {"name": "sender", "type": "address"},
                {"name": "receiver", "type": "address"}
            ]}
        ],
        "name": "emitEventWithTransfers",
        "outputs": [],
        "stateMutability": "payable",  # Marked as payable so that native tokens can be sent.
        "type": "function"
    }
]
logging.info("Contract ABI loaded.")

# Create contract instance
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Initialize counters for tracking successes and failures
total_districts = len(data.get("districts", []))
success_count = 0
failure_count = 0

# Loop through each district in the JSON file
for district in data["districts"]:
    logging.info(f"Processing District ID: {district['districtId']}")
    district_success = True

    # Prepare token transfers and convert addresses to checksum
    try:
        tokens_to_transfer = [
            (
                token,
                details["amount"],
                web3.to_checksum_address(details["receiver"]),
                web3.to_checksum_address(details["contract"])
            )
            for token, details in district["tokens"].items()
        ]
        logging.info("Token transfer data prepared.")
    except Exception as e:
        logging.error("Error while preparing token transfers for district %s: %s", district["districtId"], e)
        district_success = False
        failure_count += 1
        continue  # Skip this district if there's an error

    # Prepare the internal (native POL) transfer: convert POL to Wei and convert addresses to checksum
    try:
        internal_amount = int(float(district["internalTransfers"]["POL"]["amount"]) * 1e18)
        internal_transfer = (
            "POL",
            internal_amount,
            web3.to_checksum_address(district["internalTransfers"]["POL"]["sender"]),
            web3.to_checksum_address(district["internalTransfers"]["POL"]["receiver"])
        )
        logging.info("Internal POL transfer prepared.")
    except Exception as e:
        logging.error("Error while preparing POL transfer for district %s: %s", district["districtId"], e)
        district_success = False
        failure_count += 1
        continue

    # Build the transaction, including the value to send (native POL)
    try:
        tx = contract.functions.emitEventWithTransfers(
            district["researchType"],          # eventId
            json.dumps(district),              # message (serialized district details)
            tokens_to_transfer,                # ERC-20 token transfers array
            internal_transfer                  # Native POL transfer tuple
        ).build_transaction({
            "from": sender_address,
            "gas": 1000000,
            "gasPrice": web3.to_wei("600.200050874", "gwei"),  # Using a lower gas price similar to successful TX
            "nonce": web3.eth.get_transaction_count(sender_address),
            "value": internal_amount           # Include the native POL value (in Wei)
        })
        logging.info("Transaction built for district %s.", district["districtId"])
    except Exception as e:
        logging.error("Error while building transaction for district %s: %s", district["districtId"], e)
        district_success = False
        failure_count += 1
        continue

    # Sign and send the transaction
    try:
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logging.info(f"Transaction sent for District {district['districtId']}: {tx_hash.hex()}")
    except Exception as e:
        logging.error("Error sending transaction for district %s: %s", district["districtId"], e)
        district_success = False
        failure_count += 1
        continue

    if district_success:
        success_count += 1

# Final log statement depending on success or failures
if success_count == total_districts:
    logging.info("All transactions executed successfully!")
else:
    logging.info("Processed transactions for %d/%d districts successfully.", success_count, total_districts)
