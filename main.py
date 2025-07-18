#synthesis.py

import json
import os
import logging
import sys
import time
from web3 import Web3
from dotenv import load_dotenv
from hexbytes import HexBytes
import requests

# Configure detailed logging to file
file_handler = logging.FileHandler("transaction_debug.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Configure minimal logging to console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

# Setup root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
)

# Load environment variables from .env file
load_dotenv()
private_key = os.getenv("PRIVATE_KEY")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logging.info("Telegram token or chat ID not found! Please check your .env file.")
    logging.debug("Telegram token or chat ID not found! Please check your .env file.")

if not private_key:
    logging.error("Private key not found! Please check your .env file.")
    raise ValueError("Private key not found! Please check your .env file.")
else:
    logging.info("Private key successfully loaded.")
    logging.debug("Private key validation successful.")

# Load transaction details from JSON file
try:
    with open("transaction_data.json", "r") as file:
        data = json.load(file)
    district_count = len(data.get('districts', []))
    logging.info(f"Transaction data loaded from JSON. Found {district_count} districts.")
    logging.debug(f"Districts data: {json.dumps(data.get('districts', []), indent=2)}")
except Exception as e:
    logging.error(f"Failed to load JSON file: {e}")
    raise

# Function to send notifications to Telegram chat(s) using the Telegram Bot API.
# Requires a valid TELEGRAM_TOKEN and a list of chat IDs to send the message to.
def send_telegram_notification(text, chat_id):
    """Send notification to Telegram."""
    if not TELEGRAM_TOKEN:
        print("Telegram token not found. Skipping notification.")
        return
        

    url_req = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={chat_id}&text={text}"
    try:
        results = requests.get(url_req)
        print(f"Telegram notification sent: {results.json()}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")


# Connect to Polygon RPC endpoint
rpc_url = "https://polygon-rpc.com"
web3 = Web3(Web3.HTTPProvider(rpc_url))
if not web3.is_connected():
    logging.error("Failed to connect to Polygon blockchain.")
    raise ConnectionError("Failed to connect to Polygon blockchain")
logging.info("Connected to Polygon blockchain.")

# Get sender address from private key
try:
    account = web3.eth.account.from_key(private_key)
    sender_address = account.address
    logging.info(f"Using sender address: {sender_address}")
    logging.debug(f"Sender address derived from private key: {sender_address}")
except Exception as e:
    logging.error(f"Error deriving sender address: {e}")
    raise

# Validate sender balance
try:
    sender_balance = web3.eth.get_balance(sender_address)
    sender_balance_pol = web3.from_wei(sender_balance, 'ether')
    logging.info(f"Sender balance: {sender_balance_pol} POL")
    if sender_balance <= 0:
        logging.error(f"Sender has insufficient POL balance: {sender_balance_pol}")
        raise ValueError(f"Insufficient balance for sender address: {sender_balance_pol} POL")
except Exception as e:
    if not isinstance(e, ValueError):
        logging.error(f"Error checking sender balance: {e}")
        raise

# Set and convert the target contract address to a checksum address
try:
    contract_address = web3.to_checksum_address("0x0B00a466AD7e747D28F599c8ecd701EEC4C2E99f")
    logging.info(f"Contract address: {contract_address}")
except Exception as e:
    logging.error(f"Error with contract address: {e}")
    raise

# Updated ABI matching exactly what we see in the successful transaction
contract_abi = [
    {
        "inputs": [
            {"name": "eventId", "type": "string"},
            {"name": "message", "type": "string"}
        ],
        "name": "emitEvent",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]
logging.debug("Contract ABI loaded.")

# Create contract instance
try:
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    logging.debug("Contract instance created.")
except Exception as e:
    logging.error(f"Error creating contract instance: {e}")
    raise

# Initialize counters for tracking successes and failures
total_districts = len(data.get("districts", []))
success_count = 0
failure_count = 0

# Configurable retry mechanism
MAX_RECEIPT_ATTEMPTS = 10  # Maximum number of attempts to get transaction receipt
RECEIPT_WAIT_TIME = 5  # Seconds to wait between receipt checks
MAX_TOTAL_WAIT_TIME = 120  # Maximum total wait time in seconds

# Process all transactions from the districts array
logging.info(f"Starting to process {total_districts} districts...")

for district in data["districts"]:
    district_id = district.get("districtId", "unknown")
    logging.info(f"\n--- Processing District ID: {district_id} ({success_count + failure_count + 1}/{total_districts}) ---")
    logging.debug(f"Full district data: {json.dumps(district, indent=2)}")
    district_success = False

    # Format eventId - should be FUEL_SYNTHESIZER_SYNTHESIS
    event_id = district.get("researchType", "FUEL_SYNTHESIZER_SYNTHESIS")
    
    # Format message as a simplified JSON string (matching the successful transaction)
    try:
        message = {
            "districtId": district_id,
            "buildingId": district.get("buildingId", 0),
            "buildingType": district.get("buildingType", "FUEL_SYNTHESIZER"),
            "researchType": district.get("researchType", "FUEL_SYNTHESIZER_SYNTHESIS")
        }
        message_json = json.dumps(message)
        logging.debug(f"Message JSON: {message_json}")
    except Exception as e:
        logging.error(f"Error creating message JSON for district {district_id}: {e}")
        failure_count += 1
        continue

    # Get current nonce for sender address
    try:
        nonce = web3.eth.get_transaction_count(sender_address)
        logging.debug(f"Current nonce for sender: {nonce}")
    except Exception as e:
        logging.error(f"Error getting nonce: {e}")
        failure_count += 1
        continue

    # Get POL amount from the internal transfer
    try:
        amount_in_pol = float(district["internalTransfers"]["POL"]["amount"])
        amount_in_wei = int(amount_in_pol * 1e18)
        logging.info(f"Transfer amount: {amount_in_pol} POL")
        logging.debug(f"Transfer amount in wei: {amount_in_wei}")
    except Exception as e:
        logging.error(f"Error calculating transfer amount: {e}")
        failure_count += 1
        continue
    
    # Use gas price from successful transaction
    gas_price = web3.to_wei(100, 'gwei')
    logging.info(f"Gas price: {web3.from_wei(gas_price, 'gwei')} Gwei")

    # Build the transaction
    try:
        tx = contract.functions.emitEvent(
            event_id,      # eventId - like "FUEL_SYNTHESIZER_SYNTHESIS"
            message_json   # message - JSON string like in successful TX
        ).build_transaction({
            "from": sender_address,
            "gas": 102000,  # Similar to successful TX gas limit
            "gasPrice": gas_price,
            "nonce": nonce,
            "value": amount_in_wei
        })
        
        # Log the transaction details for debugging
        tx_details = {
            "from": tx["from"],
            "to": tx["to"],
            "value": f"{web3.from_wei(tx['value'], 'ether')} POL",
            "gas": tx["gas"],
            "gasPrice": f"{web3.from_wei(tx['gasPrice'], 'gwei')} Gwei",
            "nonce": tx["nonce"]
        }
        logging.debug(f"Transaction details: {json.dumps(tx_details, indent=2)}")
        
    except Exception as e:
        logging.error(f"Error building transaction for district {district_id}: {e}")
        failure_count += 1
        continue

    # # Ask for confirmation before sending
    # confirmation = input(f"Ready to send transaction for District {district_id}. Proceed? (y/n): ")
    # if confirmation.lower() != 'y':
    #     logging.info(f"Transaction for District {district_id} skipped by user.")
    #     continue

    # Sign and send the transaction
    try:
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = HexBytes(tx_hash).hex()
        logging.info(f"Transaction sent: {tx_hash_hex}")
        logging.debug(f"Full transaction hash: {tx_hash_hex}")
        
        # Wait for transaction receipt with controlled retry mechanism
        logging.info("Waiting for transaction confirmation...")
        start_time = time.time()
        receipt = None
        for attempt in range(MAX_RECEIPT_ATTEMPTS):
            try:
                receipt = web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    break
            except Exception as e:
                logging.debug(f"Receipt check attempt {attempt + 1} failed: {e}")
            
            # Check total wait time
            if time.time() - start_time > MAX_TOTAL_WAIT_TIME:
                logging.error("Maximum total wait time exceeded.")
                break
            
            # Wait before next attempt
            time.sleep(RECEIPT_WAIT_TIME)
        
        # Check receipt status
        if receipt:
            if receipt.get('status') == 1:
                logging.info(f"Transaction succeeded! Gas used: {receipt['gasUsed']}")
                success_count += 1
                district_success = True
            else:
                logging.error(f"Transaction failed! Gas used: {receipt['gasUsed']}")
                failure_count += 1
        else:
            logging.error("Could not retrieve transaction receipt.")
            failure_count += 1
        
    except Exception as e:
        logging.error(f"Error sending transaction for district {district_id}: {e}")
        failure_count += 1
        continue

    # Optional: Add a delay between transactions to avoid nonce issues
    if district_id != data["districts"][-1].get("districtId", "unknown"):
        time.sleep(60)  # 2 second delay between transactions

# Final log statement depending on success or failures
logging.info("\n--- SUMMARY ---")
logging.info(f"Processed: {success_count + failure_count}/{total_districts} districts")
logging.info(f"Successful: {success_count}/{total_districts}")
logging.info(f"Failed: {failure_count}/{total_districts}")

# Send summary notification to Telegram
notification = f"Processed: {success_count + failure_count}/{total_districts} districts\n" \
                f"Successful: {success_count}/{total_districts}\n" \
                f"Failed: {failure_count}/{total_districts}"
send_telegram_notification(notification, TELEGRAM_CHAT_ID)

# Final log statement depending on success or failures
if success_count == total_districts:
    logging.info("All transactions executed successfully!")
elif success_count > 0:
    logging.info(f"Partial success: {success_count}/{total_districts} transactions completed.")
else:
    logging.error("All transactions failed.")

# Exit the script to prevent any potential hanging
sys.exit(0)
