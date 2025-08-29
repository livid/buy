# buy-cli

A small CLI to buy a token on Solana using Jupiter swap API, with the token mint configured in `config.py`.

- Validates amount of SOL (first arg)
- Builds swap using Jupiter's official API (`/swap/v1/`) and signs with `id.json` keypair

## Setup

- Ensure `config.py` contains:
  - `mint`: token mint to buy
  - `rpc`: your RPC endpoint URL
- Place your Solana keypair in `id.json` (array of 64 or 32 integers)
- Optional: Set `JUPITER_API_KEY` environment variable for higher rate limits

Create venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## id.json Keypair

The `id.json` file contains your Solana keypair and should be treated with extreme care as it controls your wallet.

### Creating a Vanity Address

You can use `solana-keygen grind` to generate a keypair with a vanity address (custom prefix):

```bash
# Generate a keypair with address starting with "Buy"
solana-keygen grind --starts-with Buy:1 --ignore-case

# Generate a keypair with address ending with "SOL"
solana-keygen grind --ends-with SOL:1 --ignore-case

# Generate a keypair with specific prefix (case-sensitive)
solana-keygen grind --starts-with abcd:1
```

This will output the keypair array that you can save to `id.json`.

`solana-keygen` can be installed via:

```
brew install solana
```

### Securing Your Keypair

**Important**: Always secure your `id.json` file with proper permissions:

```bash
# Set read-only permissions for owner only
chmod 600 id.json

# Verify permissions
ls -la id.json
# Should show: -rw------- 1 user group size date id.json
```

**Security Best Practices:**
- Never share your `id.json` file or commit it to version control
- Keep backups in secure, encrypted storage
- Consider using a hardware wallet for large amounts
- Use a separate keypair for testing/development

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

**API Information:**
- Uses Jupiter's official API endpoints (`lite-api.jup.ag/swap/v1/`)
- Supports optional API key for paid plans (set `JUPITER_API_KEY` environment variable)
- Free tier available without API key

Note: Uses Jupiter's current swap API and your RPC from `config.py`.
