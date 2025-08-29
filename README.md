# buy-cli

A small CLI to buy a token on Solana using Jupiter swap API, with the token mint configured in `config.py`.

- Validates amount of SOL (first arg)
- Builds swap using Jupiter v6 and signs with `id.json` keypair

## Setup

- Ensure `config.py` contains:
  - `mint`: token mint to buy
  - `rpc`: your RPC endpoint URL
- Place your Solana keypair in `id.json` (array of 64 or 32 integers)

Create venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Dry-run (build but do not send):

```bash
python buy.py 0.005
```

Broadcast:

```bash
python buy.py 0.005 --no-dry-run --yes
```

Options:
- `--slippage-bps` default 100 (1%)
- `--priority-fee` lamports or `auto`
- `--yes` skip confirmation
- `--no-dry-run` to broadcast

Note: Uses Jupiter quote/swap APIs and your RPC from `config.py`.
