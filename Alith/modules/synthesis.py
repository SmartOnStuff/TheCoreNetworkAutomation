# synthesis.py
# Module for performing synthesis operations on The Core Network platform

import json
import os
import logging
import time
from web3 import Web3
from hexbytes import HexBytes
import requests


def send_telegram_notification(text, chat_id, token):
    """
    Send notification to Telegram.
    
    Args:
        text (str): Message text to send
        chat_id (str): Telegram chat ID
        token (str): Telegram bot token
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not token:
        logging.info("Telegram token not found. Skipping notification.")
        return False
        
    url_req = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}"
    try:
        results = requests.get(url_req)
        logging.info(f"Telegram notification sent: {results.json()}")
        return True
    except Exception as e:
        logging.error(f"Error sending Telegram notification: {e}")
        return False


def perform_synthesis(district_data):
    """
    Perform synthesis operation for a district.
    
    Args:
        district_data (dict): District data containing all necessary information for synthesis
    
    Returns:
        dict: Result of the synthesis operation with status and details
    """
    # Load environment variables 
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get environment variables
    private_key = os.getenv("PRIVATE_KEY")
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Validate required environment variables
    if not private_key:
        error_msg = "Private key not found! Please check your .env file."
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Connect to Polygon RPC endpoint
    rpc_url = "https://polygon-rpc.com"
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        error_msg = "Failed to connect to Polygon blockchain."
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    logging.info("Connected to Polygon blockchain.")
    
    # Get sender address from private key
    try:
        account = web3.eth.account.from_key(private_key)
        sender_address = account.address
        logging.info(f"Using sender address: {sender_address}")
    except Exception as e:
        error_msg = f"Error deriving sender address: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Validate sender balance
    try:
        sender_balance = web3.eth.get_balance(sender_address)
        sender_balance_pol = web3.from_wei(sender_balance, 'ether')
        logging.info(f"Sender balance: {sender_balance_pol} POL")
        if sender_balance <= 0:
            error_msg = f"Insufficient balance for sender address: {sender_balance_pol} POL"
            logging.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
    except Exception as e:
        error_msg = f"Error checking sender balance: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Set and convert the target contract address to a checksum address
    try:
        contract_address = web3.to_checksum_address("0x0B00a466AD7e747D28F599c8ecd701EEC4C2E99f")
        logging.info(f"Contract address: {contract_address}")
    except Exception as e:
        error_msg = f"Error with contract address: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Contract ABI
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
    
    # Create contract instance
    try:
        contract = web3.eth.contract(address=contract_address, abi=contract_abi)
        logging.info("Contract instance created.")
    except Exception as e:
        error_msg = f"Error creating contract instance: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Extract district information
    district_id = district_data.get("districtId", "unknown")
    logging.info(f"Processing District ID: {district_id}")
    
    # Format eventId - should be FUEL_SYNTHESIZER_SYNTHESIS
    event_id = district_data.get("researchType", "FUEL_SYNTHESIZER_SYNTHESIS")
    
    # Format message as a simplified JSON string
    try:
        message = {
            "districtId": district_id,
            "buildingId": district_data.get("buildingId", 0),
            "buildingType": district_data.get("buildingType", "FUEL_SYNTHESIZER"),
            "researchType": district_data.get("researchType", "FUEL_SYNTHESIZER_SYNTHESIS")
        }
        message_json = json.dumps(message)
        logging.info(f"Message JSON: {message_json}")
    except Exception as e:
        error_msg = f"Error creating message JSON for district {district_id}: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Get current nonce for sender address
    try:
        nonce = web3.eth.get_transaction_count(sender_address)
        logging.info(f"Current nonce for sender: {nonce}")
    except Exception as e:
        error_msg = f"Error getting nonce: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Get POL amount from the internal transfer
    try:
        amount_in_pol = float(district_data["internalTransfers"]["POL"]["amount"])
        amount_in_wei = int(amount_in_pol * 1e18)
        logging.info(f"Transfer amount: {amount_in_pol} POL")
    except Exception as e:
        error_msg = f"Error calculating transfer amount: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Use gas price from successful transaction
    gas_price = web3.to_wei(50.126386178, 'gwei')
    logging.info(f"Gas price: {web3.from_wei(gas_price, 'gwei')} Gwei")
    
    # Build the transaction
    try:
        tx = contract.functions.emitEvent(
            event_id,      # eventId - like "FUEL_SYNTHESIZER_SYNTHESIS"
            message_json   # message - JSON string
        ).build_transaction({
            "from": sender_address,
            "gas": 102000,  # Gas limit
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
        logging.info(f"Transaction details: {json.dumps(tx_details, indent=2)}")
        
    except Exception as e:
        error_msg = f"Error building transaction for district {district_id}: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }
    
    # Sign and send the transaction
    try:
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = HexBytes(tx_hash).hex()
        logging.info(f"Transaction sent: {tx_hash_hex}")
        
        # Wait for transaction receipt with controlled retry mechanism
        logging.info("Waiting for transaction confirmation...")
        max_receipt_attempts = 10
        receipt_wait_time = 5
        
        start_time = time.time()
        receipt = None
        
        for attempt in range(max_receipt_attempts):
            try:
                receipt = web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    break
            except Exception as e:
                logging.info(f"Receipt check attempt {attempt + 1} failed: {e}")
            
            # Wait before next attempt
            time.sleep(receipt_wait_time)
        
        # Check receipt status
        if receipt:
            if receipt.get('status') == 1:
                success_msg = f"Transaction succeeded! Gas used: {receipt['gasUsed']}"
                logging.info(success_msg)
                
                # Send telegram notification if configured
                if telegram_token and telegram_chat_id:
                    notification = f"Synthesis successful!\nDistrict: {district_id}\nTx: {tx_hash_hex}\nGas used: {receipt['gasUsed']}"
                    send_telegram_notification(notification, telegram_chat_id, telegram_token)
                
                return {
                    "success": True,
                    "message": success_msg,
                    "tx_hash": tx_hash_hex,
                    "gas_used": receipt['gasUsed']
                }
            else:
                error_msg = f"Transaction failed! Gas used: {receipt['gasUsed']}"
                logging.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "tx_hash": tx_hash_hex
                }
        else:
            error_msg = "Could not retrieve transaction receipt."
            logging.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "tx_hash": tx_hash_hex
            }
        
    except Exception as e:
        error_msg = f"Error sending transaction for district {district_id}: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "message": error_msg
        }


def run_synthesis_for_districts(districts_data):
    """
    Run synthesis for multiple districts.
    
    Args:
        districts_data (list): List of district data objects
        
    Returns:
        dict: Summary of synthesis operations with success and failure counts
    """
    if not districts_data:
        return {
            "success": False,
            "message": "No districts provided for synthesis"
        }
    
    total_districts = len(districts_data)
    success_count = 0
    failure_count = 0
    results = []
    
    for district in districts_data:
        result = perform_synthesis(district)
        results.append({
            "district_id": district.get("districtId", "unknown"),
            "result": result
        })
        
        if result["success"]:
            success_count += 1
        else:
            failure_count += 1
        
        # Add a delay between transactions to avoid nonce issues
        if district != districts_data[-1]:
            time.sleep(2)
    
    # Create summary
    summary = {
        "total": total_districts,
        "successful": success_count,
        "failed": failure_count,
        "details": results
    }
    
    # Send summary notification to Telegram
    from dotenv import load_dotenv
    load_dotenv()
    
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if telegram_token and telegram_chat_id:
        notification = f"Synthesis Summary:\n" \
                      f"Processed: {success_count + failure_count}/{total_districts} districts\n" \
                      f"Successful: {success_count}/{total_districts}\n" \
                      f"Failed: {failure_count}/{total_districts}"
        send_telegram_notification(notification, telegram_chat_id, telegram_token)
    
    return summary