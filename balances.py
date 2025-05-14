import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Function to send notifications to Telegram chat(s) using the Telegram Bot API
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


def format_number(value, decimals=0):
    """
    Format a number with apostrophes as thousand separators.
    If decimals is specified, round to that many decimal places.
    
    Args:
        value (float): The number to format
        decimals (int): Number of decimal places to show
    
    Returns:
        str: Formatted number string
    """
    if decimals > 0:
        # Round to specified decimal places
        rounded_value = round(value, decimals)
        # Split into integer and decimal parts
        int_part, dec_part = str(rounded_value).split('.')
        # Pad decimal part if needed
        dec_part = dec_part.ljust(decimals, '0')
        # Format integer part with apostrophes
        formatted_int = ''
        for i, char in enumerate(reversed(int_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = "'" + formatted_int
            formatted_int = char + formatted_int
        # Combine parts
        return f"{formatted_int}.{dec_part[:decimals]}"
    else:
        # Format integer with apostrophes
        int_value = int(value)
        formatted = ''
        for i, char in enumerate(reversed(str(int_value))):
            if i > 0 and i % 3 == 0:
                formatted = "'" + formatted
            formatted = char + formatted
        return formatted


def get_polygon_token_balances(wallet_address: str, api_key: str) -> str:
    """
    Get token balances for a wallet address on Polygon network using v2 API with chainid parameter.
    
    Args:
        wallet_address (str): The wallet address to check
        api_key (str): Your Etherscan/Polygonscan API key
        
    Returns:
        str: Formatted string with token balances on separate lines with aligned columns
    """
    # Validate inputs
    if not wallet_address or not api_key:
        return "Error: Wallet address and API key are required"
    
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        return "Error: Invalid wallet address format"
    
    # Token addresses to check (including MATIC/POL)
    tokens = {
        "POL": "native",  # MATIC/POL native token
        "Si": "0xD2fDBb49DBA431fb728a046c5900618deED064fF",
        "REE": "0x813a5B8eE3932B5ce1c4B2b6444d599A128a6C71",
        "C": "0xf986430B685e9aB18E0108C604d31b71971DB5F7",
        "Ti": "0xF53CE43b19f04E84890E3c347Dc4A366f3D75619",
        "H": "0x6989f166E49b378D38c4A5d2b00D76344dEa8Cec",
        "He3": "0xc316115D4ce93Af8E081d8555820fF74eFD5b5AE",
        "COS": "0x2c6e0C3EC2107144CcbadD6b003eC13b72EB44E7",
        "CN": "0x7BeD50d99CfdBea233A2F2E3DCCd4F9A0acAfe6c",
        "CRS": "0x4F80a7627bfb9fdc54d7184e0DDeB2c76596cC3C"
    }
    
    # Token decimals - assuming all are 18 but can be adjusted if needed
    token_decimals = {
        "POL": 18,
        "Si": 0,
        "REE": 0,
        "C": 0,
        "Ti": 0,
        "H": 0,
        "He3": 0,
        "COS": 0,
        "CN": 0,
        "CRS": 0
    }
    
    results = []
    token_values = {}  # Store token values for aligned formatting later
    # Using proper base URL for v2 API from Etherscan
    base_url = "https://api.etherscan.io/v2/api"
    # Polygon chainid is 137
    chain_id = 137
    
    try:
        # First get POL (MATIC) balance - native token
        polygon_params = {
            "chainid": chain_id,
            "module": "account",
            "action": "balance",
            "address": wallet_address,
            "apikey": api_key
        }
        
        response = requests.get(base_url, params=polygon_params)
        data = response.json()
        
        if data["status"] == "1":
            # Convert from wei to MATIC/POL (18 decimals)
            balance = float(data["result"]) / (10 ** token_decimals["POL"])
            # Format with 3 decimal places
            formatted_balance = format_number(balance, 3)
            token_values["POL"] = formatted_balance
        else:
            token_values["POL"] = f"Error fetching balance - {data.get('message', 'Unknown error')}"
        
        # Get balances for other tokens
        for symbol, token_address in tokens.items():
            # Skip POL as we already got it
            if symbol == "POL":
                continue
            
            # Use the tokenbalance endpoint with v2 API format
            token_params = {
                "chainid": chain_id,
                "module": "account",
                "action": "tokenbalance",
                "contractaddress": token_address,
                "address": wallet_address,
                "tag": "latest",
                "apikey": api_key
            }
            
            try:
                token_response = requests.get(base_url, params=token_params)
                token_data = token_response.json()
                
                if token_data["status"] == "1":
                    # For tokens with 0 decimals, we don't need to divide
                    decimals = token_decimals.get(symbol, 0)
                    token_balance = float(token_data["result"])
                    if decimals > 0:
                        token_balance = token_balance / (10 ** decimals)
                    
                    # Format without decimal places for integer tokens
                    formatted_token_balance = format_number(token_balance, 0)
                    token_values[symbol] = formatted_token_balance
                else:
                    token_values[symbol] = f"Error fetching balance - {token_data.get('message', 'Unknown error')}"
                
                # Add a small delay to prevent API rate limiting
                time.sleep(0.5)
            except Exception as e:
                token_values[symbol] = f"Error - {str(e)}"
        
        # Format the results with aligned columns
        # Find the length of the longest token symbol for padding
        max_symbol_length = max(len(symbol) for symbol in tokens.keys())
        
        # Create formatted output with aligned columns
        for symbol in tokens.keys():
            if symbol in token_values:
                # Pad the token symbol to align values
                results.append(f"{token_values[symbol]}{' ' * (max_symbol_length - len(symbol) + 5)}{symbol}")
        
        return "\n".join(results)
    
    except Exception as e:
        return f"Error fetching balances: {str(e)}"


if __name__ == "__main__":
    # Example usage
    wallet_address = WALLET_ADDRESS
    api_key = ETHERSCAN_API_KEY
    
    if not wallet_address or not api_key:
        print("Please set WALLET_ADDRESS and ETHERSCAN_API_KEY in your .env file")
    else:
        result = get_polygon_token_balances(wallet_address, api_key)
        print(result)
        
        # Send the results to Telegram if configured
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            send_telegram_notification(result, TELEGRAM_CHAT_ID)
        else:
            print("Telegram notification skipped: missing token or chat ID")
