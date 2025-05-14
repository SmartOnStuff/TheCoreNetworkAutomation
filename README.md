# TheCoreNetworkAutomation
automations for the Core Network game

This tool automates the process of fuel synthesis for the Core Network on the Polygon blockchain. It's designed to process transaction data from a JSON file and emit events through a contract while handling error logging, retries, and notifications.

## Deployment Options

### 1. GitHub Actions (Automated Execution)

This option allows the script to run automatically at 2:00 AM UTC without requiring your local machine to be running.

#### Setup Steps:

1. **Fork/Clone the Repository to Your GitHub Account**

2. **Set Up GitHub Secrets**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `PRIVATE_KEY`: Your Polygon wallet private key
     - `TELEGRAM_TOKEN`: Your Telegram bot token (optional)
     - `TELEGRAM_CHAT_ID`: Your Telegram chat ID (optional)

3. **Enable Workflow Permissions**
   - Go to Settings → Actions → General
   - Under "Workflow permissions", select "Read and write permissions"
   - Save changes

4. **Update `transaction_data.json`**
   - Modify the transaction data file with your specific district information
   - Commit and push the changes

The workflow will automatically run at 2:00 AM UTC every day.

### 2. Local Execution

This option gives you direct control over when the script runs and allows for immediate debugging.

#### Setup Steps:

1. **Clone the Repository**
   ```bash
   git clone [repository-url]
   cd [repository-directory]
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file and add your credentials:
   ```
   PRIVATE_KEY=your_polygon_wallet_private_key
   TELEGRAM_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

4. **Update Transaction Data**
   - Edit `transaction_data.json` with your district information (see format below)

5. **Run the Script**
   ```bash
   python main.py
   ```

## Configuration Files

### transaction_data.json

This file contains the district information that will be processed. Example format:

```json
{
  "districts": [
    {
      "districtId": "12345",
      "buildingId": 67890,
      "buildingType": "FUEL_SYNTHESIZER",
      "researchType": "FUEL_SYNTHESIZER_SYNTHESIS",
      "internalTransfers": {
        "POL": {
          "amount": "0.05"
        }
      }
    },
    {
      "districtId": "67890",
      "buildingId": 12345,
      "buildingType": "FUEL_SYNTHESIZER",
      "researchType": "FUEL_SYNTHESIZER_SYNTHESIS",
      "internalTransfers": {
        "POL": {
          "amount": "0.07"
        }
      }
    }
  ]
}
```

### .env

Contains sensitive environment variables:

```
PRIVATE_KEY=your_polygon_wallet_private_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

## How It Works

1. **Initialization**:
   - Loads environment variables and transaction data
   - Sets up logging to both console and file
   - Validates the private key and confirms blockchain connection

2. **For Each District**:
   - Prepares the transaction data for the contract call
   - Calculates the amount of POL to send
   - Signs and sends the transaction
   - Waits for confirmation with a retry mechanism
   - Logs success or failure

3. **Notifications**:
   - Sends summary notifications via Telegram when complete

## Logging and Monitoring

- Detailed logs are written to `transaction_debug.log`
- Basic information is output to the console
- Transaction summaries are sent to Telegram (if configured)

## Error Handling

The script includes comprehensive error handling:
- Connection errors
- Insufficient balance checks
- Transaction failures
- Receipt retrieval retries

## Contract Interaction Details

The script interacts with a contract at address `0x0B00a466AD7e747D28F599c8ecd701EEC4C2E99f` on Polygon, calling the `emitEvent` function with:

- `eventId`: Usually "FUEL_SYNTHESIZER_SYNTHESIS"
- `message`: A JSON string containing district information

## Troubleshooting

If you encounter issues:

1. **Check Logs**: Examine `transaction_debug.log` for detailed error information
2. **Verify Balance**: Ensure your wallet has sufficient POL for transactions
3. **Network Status**: Confirm the Polygon network is operational
4. **Gas Settings**: You may need to adjust gas price during high network congestion
