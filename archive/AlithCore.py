#!/usr/bin/env python3
# alith.py - Main file for The Core Network Agent

import os
import json
import logging
from typing import Dict, Any, List
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
)
from alith import Agent
from dotenv import load_dotenv
from web3 import Web3

# Import module functions
from modules.balances import check_balances
from modules.synthesis import run_synthesis_for_districts
from modules.mintdistrict import mint_district

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Validate wallet address if available
if WALLET_ADDRESS:
    try:
        WALLET_ADDRESS = Web3.to_checksum_address(WALLET_ADDRESS)
    except Exception as e:
        logger.warning(f"Invalid wallet address format: {e}")


#=======================================================================
# Tool Functions for the Alith Agent
#=======================================================================

def get_balances(wallet_address: str = None) -> str:
    """
    Get token balances for a wallet
    
    Args:
        wallet_address: The wallet address to check (optional, uses env var if not provided)
        
    Returns:
        str: Formatted balance information
    """
    try:
        # Use provided wallet address or fall back to env variable
        address = wallet_address if wallet_address else WALLET_ADDRESS
        
        if not address:
            return "Error: No wallet address provided or found in environment variables"
        
        # Call the balances module function
        balances = check_balances(address)
        return f"Token Balances for {address}:\n\n{balances}"
    except Exception as e:
        logger.error(f"Error checking balances: {e}")
        return f"Error checking balances: {str(e)}"


def perform_synthesis() -> str:
    """
    Perform synthesis for districts defined in districts.json
    
    Returns:
        str: Result of synthesis operations
    """
    try:
        # Load districts data from JSON file
        districts_path = os.path.join(os.path.dirname(__file__), 'districts.json')
        
        if not os.path.exists(districts_path):
            return "Error: Districts file not found. Expected at: /alith/districts.json"
        
        with open(districts_path, 'r') as file:
            data = json.load(file)
        
        districts = data.get('districts', [])
        
        if not districts:
            return "No districts found for synthesis in districts.json"
        
        logger.info(f"Found {len(districts)} districts for synthesis")
        
        # Run synthesis for all districts
        results = run_synthesis_for_districts(districts)
        
        # Format response
        summary = (
            f"Synthesis Summary:\n"
            f"✅ Successful: {results['successful']}/{results['total']}\n"
            f"❌ Failed: {results['failed']}/{results['total']}\n\n"
            f"Detailed Results:\n"
        )
        
        for detail in results['details']:
            district_id = detail['district_id']
            result = detail['result']
            
            if result['success']:
                summary += f"District {district_id}: ✅ Success - Tx: {result.get('tx_hash', 'N/A')}\n"
            else:
                summary += f"District {district_id}: ❌ Failed - {result.get('message', 'Unknown error')}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error performing synthesis: {e}")
        return f"Error performing synthesis: {str(e)}"


def mint_new_district(district_name: str, location: str) -> str:
    """
    Mint a new district (placeholder for future implementation)
    
    Args:
        district_name: Name for the new district
        location: Location coordinates or identifier
        
    Returns:
        str: Result of district minting attempt
    """
    try:
        # Create parameters dictionary
        params = {
            "district_name": district_name,
            "location": location
        }
        
        # Call the mintdistrict module function
        result = mint_district(params)
        
        # For now, this will return the placeholder message
        return f"District Minting Request:\n\nName: {district_name}\nLocation: {location}\n\n{result['message']}"
    except Exception as e:
        logger.error(f"Error minting district: {e}")
        return f"Error minting district: {str(e)}"


#=======================================================================
# Telegram Bot Setup
#=======================================================================

def setup_telegram_bot():
    """Set up and run the Telegram bot"""
    
    # Initialize Alith Agent with our Core Network tools
    agent = Agent(
        name="Core Network Agent",
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url="api.deepseek.com",
        preamble="""You are an advanced AI assistant for The Core Network web3 gaming platform. 
        You can check token balances, perform synthesis operations for districts, and handle district minting requests.""",
        tools=[get_balances, perform_synthesis, mint_new_district],
    )
    
    # Initialize Telegram Bot
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Define message handler
    async def handle_message(update: Update, context: CallbackContext) -> None:
        # Use the agent to generate a response
        response = agent.prompt(update.message.text)
        # Send the reply back to the Telegram chat
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    
    # Add handlers to the application
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Start the bot
    logger.info("Starting Telegram bot")
    app.run_polling()


if __name__ == "__main__":
    setup_telegram_bot()