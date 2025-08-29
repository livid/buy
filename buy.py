"""
Jupiter-only CLI to buy the token in config.py, spending a SOL amount.

Usage:
  python buy.py 0.005 [--slippage-bps 100] [--priority-fee auto] [--yes] [--no-dry-run]
"""

import base64
import json
import sys
import os
from dataclasses import dataclass
from typing import Optional

import click
import requests
import base58

from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from requests import JSONDecodeError

import config


LAMPORTS_PER_SOL = 1_000_000_000

# Use the official Jupiter API endpoints
# Free tier users should use lite-api.jup.ag. api.jup.ag is for paid plans and requires an API key
API_KEY = os.getenv("JUPITER_API_KEY")  # Optional API key for paid plans
API_BASE_URL = "https://api.jup.ag" if API_KEY else "https://lite-api.jup.ag"

SOL_MINT = "So11111111111111111111111111111111111111112"


@dataclass
class SwapResult:
    signature: str
    explorer_url: str
    sim_err: Optional[str] = None
    sim_logs: Optional[list[str]] = None


def load_keypair_from_id_json(path: str = "id.json") -> Keypair:
    """Load keypair from id.json file - supports both JSON array and base58 formats."""
    with open(path, "r", encoding="utf8") as f:
        data = json.load(f)
    
    # Handle JSON array format (standard Solana CLI format)
    if isinstance(data, list) and all(isinstance(x, int) for x in data):
        secret = bytes(data)
        if len(secret) == 64:
            return Keypair.from_bytes(secret)
        if len(secret) == 32:
            return Keypair.from_seed(secret)
        raise ValueError("id.json array must contain 32 or 64 bytes")
    
    # Handle base58 string format (like Jupiter examples)
    if isinstance(data, str):
        try:
            private_key_bytes = base58.b58decode(data)
            return Keypair.from_bytes(private_key_bytes)
        except Exception as e:
            raise ValueError(f"Invalid base58 private key: {e}")
    
    raise ValueError(
        "id.json must be a JSON array of integers or base58 string"
    )


def jupiter_quote(amount_lamports: int, out_mint: str, slippage_bps: int) -> dict:
    """Get a quote from Jupiter using the new API format."""
    # Set up headers for API requests (include x-api-key if API_KEY is available)
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    
    params = {
        "inputMint": SOL_MINT,
        "outputMint": out_mint,
        "amount": str(amount_lamports),
        "slippageBps": str(slippage_bps),
    }
    
    quote_endpoint = f"{API_BASE_URL}/swap/v1/quote"
    r = requests.get(quote_endpoint, params=params, headers=headers, timeout=20)
    
    if r.status_code != 200:
        try:
            error_data = r.json()
            raise RuntimeError(f"Jupiter quote error: {error_data}")
        except JSONDecodeError:
            raise RuntimeError(f"Jupiter quote error: {r.text}")
    
    return r.json()


def jupiter_swap_tx(
    quote: dict,
    user_pubkey: str,
    prioritization_fee_lamports: Optional[int] = None,
) -> str:
    """Get a swap transaction from Jupiter using the new API format."""
    # Set up headers for API requests (include x-api-key if API_KEY is available)
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    
    body = {
        "userPublicKey": user_pubkey,
        "quoteResponse": quote,
        "wrapAndUnwrapSol": True,
        "asLegacyTransaction": False,
        "useSharedAccounts": True,
        "dynamicComputeUnitLimit": True,
    }
    
    if prioritization_fee_lamports is not None:
        body["prioritizationFeeLamports"] = prioritization_fee_lamports
    
    swap_endpoint = f"{API_BASE_URL}/swap/v1/swap"
    r = requests.post(swap_endpoint, json=body, headers=headers, timeout=30)
    
    if r.status_code != 200:
        try:
            error_data = r.json()
            raise RuntimeError(f"Jupiter swap error: {error_data}")
        except JSONDecodeError:
            raise RuntimeError(f"Jupiter swap error: {r.text}")
    
    data = r.json()
    if "swapTransaction" not in data:
        raise RuntimeError(f"Jupiter swap response missing transaction: {data}")
    return data["swapTransaction"]


def send_signed_tx(b64_tx: str, kp: Keypair, rpc_url: str) -> SwapResult:
    """Sign and send transaction using Jupiter's approach."""
    # Get Raw Transaction
    swap_transaction_bytes = base64.b64decode(b64_tx)
    raw_transaction = VersionedTransaction.from_bytes(swap_transaction_bytes)
    
    # Sign Transaction (Jupiter approach)
    account_keys = raw_transaction.message.account_keys
    wallet_index = account_keys.index(kp.pubkey())
    
    signers = list(raw_transaction.signatures)
    signers[wallet_index] = kp
    
    signed_transaction = VersionedTransaction(raw_transaction.message, signers)
    
    # Send the signed transaction to the RPC client
    client = Client(rpc_url)
    
    # Proactive simulation to surface errors/logs
    try:
        sim_resp = client.simulate_transaction(signed_transaction, sig_verify=False)
        sim_val = sim_resp.value
        sim_err = getattr(sim_val, "err", None)
        sim_logs = getattr(sim_val, "logs", None)
    except Exception:
        sim_err = None
        sim_logs = None
    
    try:
        rpc_response = client.send_transaction(signed_transaction)
        sig = str(rpc_response.value)
        url = f"https://solscan.io/tx/{sig}"
        
        # Try to pull status to surface RPC-side error messages
        try:
            status = client.get_signature_statuses([sig]).value
            if status and status[0] and getattr(status[0], "err", None):
                sim_err = sim_err or str(status[0].err)
        except Exception:
            pass
            
        return SwapResult(
            signature=sig,
            explorer_url=url,
            sim_err=sim_err,
            sim_logs=sim_logs
        )
    except RPCException as e:
        error_message = e.args[0]
        print("Transaction failed!")
        try:
            error_code = error_message.data.err.err.code
            print(f"Custom Program Error Code: {error_code}")
        except Exception:
            pass
        print(f"Message: {error_message.message}")
        raise RuntimeError(f"Transaction failed: {error_message.message}")


def simulate_swap(
    b64_tx: str, kp: Keypair, rpc_url: str
) -> tuple[Optional[str], Optional[list[str]]]:
    """Build a signed transaction and simulate it (Jupiter approach)."""
    # Get Raw Transaction
    swap_transaction_bytes = base64.b64decode(b64_tx)
    raw_transaction = VersionedTransaction.from_bytes(swap_transaction_bytes)
    
    # Sign Transaction (Jupiter approach)
    account_keys = raw_transaction.message.account_keys
    wallet_index = account_keys.index(kp.pubkey())
    
    signers = list(raw_transaction.signatures)
    signers[wallet_index] = kp
    
    signed_transaction = VersionedTransaction(raw_transaction.message, signers)

    client = Client(rpc_url)
    try:
        sim_resp = client.simulate_transaction(signed_transaction, sig_verify=False)
        sim_val = sim_resp.value
        return getattr(sim_val, "err", None), getattr(sim_val, "logs", None)
    except Exception:
        return None, None


def validate_amount(ctx, param, value) -> float:
    try:
        amt = float(value)
    except Exception:
        raise click.BadParameter("Amount must be a number, e.g. 0.005") from None
    if amt <= 0:
        raise click.BadParameter("Amount must be greater than 0")
    return amt


@click.command("buy")
@click.argument("amount", callback=validate_amount)
@click.option("--slippage-bps", default=100, show_default=True, help="Max slippage in basis points")
@click.option("--priority-fee", "priority_fee", default="50000", show_default=True, help="Prioritization fee in lamports or 'auto'")
@click.option("--yes", is_flag=True, help="Skip confirmation and broadcast the transaction")
@click.option("--dry-run/--no-dry-run", default=True, show_default=True, help="Build transaction without sending")
def main(amount: float, slippage_bps: int, priority_fee: str, yes: bool, dry_run: bool):
    """Buy the token in config.py spending AMOUNT SOL via Jupiter. Example: 0.005"""

    mint = config.mint
    rpc_url = config.rpc

    click.echo(f"Token mint: {mint}")
    click.echo(f"RPC: {rpc_url}")
    click.echo(f"Amount SOL: {amount}")

    # 1) Load wallet
    try:
        kp = load_keypair_from_id_json("id.json")
    except Exception as e:
        click.echo(f"Failed to load wallet from id.json: {e}", err=True)
        sys.exit(1)
    pubkey = str(kp.pubkey())
    click.echo(f"Wallet: {pubkey}")

    # 2) Build buy transaction via Jupiter
    try:
        prio = None if priority_fee == "auto" else int(priority_fee)
        lamports = int(float(amount) * LAMPORTS_PER_SOL)
        quote = jupiter_quote(lamports, mint, slippage_bps)
        b64_tx = jupiter_swap_tx(quote, pubkey, prio)
    except Exception as e:
        click.echo(f"Failed to build buy transaction: {e}", err=True)
        sys.exit(1)

    if dry_run and not yes:
        err, logs = simulate_swap(b64_tx, kp, rpc_url)
        click.echo("Dry-run simulation (not sent):")
        if err is not None:
            click.echo("RPC simulate error:")
            click.echo(str(err))
        if logs:
            click.echo("Logs:")
            for line in logs[:50]:
                click.echo(f"  {line}")
        click.echo("Dry-run complete. Use --no-dry-run or --yes to broadcast.")
        return

    if not yes:
        click.confirm("Proceed to send the transaction?", abort=True)

    # 3) Sign and send
    try:
        result = send_signed_tx(b64_tx, kp, rpc_url)
    except Exception as e:
        click.echo(f"Broadcast failed: {e}", err=True)
        sys.exit(1)

    click.echo(f"Tx signature: {result.signature}")
    click.echo(f"Explorer: {result.explorer_url}")
    if result.sim_err is not None:
        click.echo("RPC simulate error:")
        click.echo(str(result.sim_err))
        if result.sim_logs:
            click.echo("Logs:")
            for line in result.sim_logs[:50]:
                click.echo(f"  {line}")


if __name__ == "__main__":
    main()

