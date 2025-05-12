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

# Load transaction details from JSON file.
# Note: Your JSON file must match the synthesis use case. For example:
# {
#   "districts": [
#     {
#       "districtId": 4343,
#       "buildingId": 254,
#       "buildingType": "FUEL_SYNTHESIZER",
#       "researchType": "FUEL_SYNTHESIZER_SYNTHESIS",
#       "tokens": {
#         "H": {
#           "amount": 1000000,
#           "receiver": "0x0000000000000000000000000000000000000000",
#           "contract": "0x6989f166e49b378d38c4a5d2b00d76344dea8cec"
#         },
#         "He3": {
#           "amount": 300000,
#           "receiver": "0x0000000000000000000000000000000000000000",
#           "contract": "0xc316115d4ce93af8e081d8555820ff74efd5b5ae"
#         }
#       },
#       "internalTransfers": {
#         "POL": {
#           "amount": 0.01,
#           "sender": "0x0B00a466AD7e747D28F599c8ecd701EEC4C2E99f",
#           "receiver": "0x4e949E971ED54b0A131761Ae38eaD5C1C3e40dCF"
#         }
#       }
#     }
#   ]
# }
try:
    with open("transaction_data.json", "r") as file:
        data = json.load(file)
    logging.info("Transaction data loaded from JSON.")
except Exception as e:
    logging.error("Failed to load JSON file: %s", e)
    raise

# Connect to the Polygon RPC endpoint
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

# Updated ABI with proper tuple component definitions.
# The function emitEventWithTransfers takes four arguments:
# 1. eventId (string)
# 2. message (string)
# 3. tokens (tuple[]): each component has (tokenId, amount, receiver, tokenContract)
# 4. internalTransfer (tuple): with (tokenId, amount, sender, receiver)
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
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
logging.info("Contract ABI loaded.")

# Create the contract instance
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Counters for tracking how many districts are processed successfully
total_districts = len(data.get("districts", []))
success_count = 0
failure_count = 0

# Process each district in the data
for district in data["districts"]:
    logging.info(f"Processing District ID: {district['districtId']}")
    district_success = True

    # Prepare token transfers and convert addresses to checksum.
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
        logging.error("Error preparing token transfers for district %s: %s", district["districtId"], e)
        district_success = False
        failure_count += 1
        continue

    # Prepare the internal (native POL) transfer: convert POL to Wei and checksum addresses.
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
        logging.error("Error preparing POL transfer for district %s: %s", district["districtId"], e)
        district_success = False
        failure_count += 1
        continue

    # First simulate the call with eth_call to verify that the inputs pass the contract logic.
    try:
        simulation_result = contract.functions.emitEventWithTransfers(
            district["researchType"],   # eventId: for synthesis, e.g. "FUEL_SYNTHESIZER_SYNTHESIS"
            json.dumps(district),       # message containing district details
            tokens_to_transfer,         # token transfers array (e.g. Hydrogen and Helium3)
            internal_transfer           # internal POL transfer tuple
        ).call({
            "from": sender_address,
            "gas": 1000000,
            "gasPrice": web3.to_wei("612.94176276", "gwei"),
            "nonce": web3.eth.get_transaction_count(sender_address)
        })
        logging.info("Call simulation result: %s", simulation_result)
    except Exception as call_err:
        logging.error("Simulated call error for district %s: %s", district["districtId"], call_err.args)
        district_success = False
        failure_count += 1
        continue  # Skip sending a transaction if simulation fails

    # Build the transaction
    try:
        tx = contract.functions.emitEventWithTransfers(
            district["researchType"],
            json.dumps(district),
            tokens_to_transfer,
            internal_transfer
        ).build_transaction({
            "from": sender_address,
            "gas": 1000000,
            "gasPrice": web3.to_wei("612.94176276", "gwei"),
            "nonce": web3.eth.get_transaction_count(sender_address)
        })
        logging.info("Transaction built for district %s.", district["districtId"])
    except Exception as e:
        logging.error("Error building transaction for district %s: %s", district["districtId"], e)
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

# Final statement depends on overall success
if success_count == total_districts:
    logging.info("All transactions executed successfully!")
else:
    logging.info("Processed transactions for %d/%d districts successfully.",
                 success_count, total_districts)
