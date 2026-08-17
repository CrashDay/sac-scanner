# Windows Setup

Use this after cloning `CrashDay/sac-scanner` on the Windows desktop.

## 1. Clone

```powershell
git clone git@github.com:CrashDay/sac-scanner.git
cd sac-scanner
```

## 2. Verify Python

```powershell
py --version
py -m unittest
```

## 3. Configure Schwab

Create or reuse a local Schwab env file. Then point the scanner at it:

```powershell
$env:SAC_SCHWAB_ENV = "C:\path\to\schwab.env"
```

The env file needs Schwab app credentials:

```text
SCHWAB_APP_KEY=...
SCHWAB_APP_SECRET=...
SCHWAB_REFRESH_TOKEN=...
SCHWAB_TOKEN_PATH=C:\path\to\schwab_tokens.json
```

If `SCHWAB_REFRESH_TOKEN` is omitted, the token cache at `SCHWAB_TOKEN_PATH`
must already contain a refresh token.

## 4. Generate The Local Universe

The universe is generated local data and is not committed.

```powershell
py -m sac_scanner refresh-universe
```

This creates:

```text
data\universe\equities.json
```

## 5. Run The Dashboard

```powershell
py -m sac_scanner.server --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

## 6. Add To Codex Desktop

In Codex on Windows, open or add the cloned `sac-scanner` folder itself as the
project. The Mac-only landing folder `/Users/tonyday/Documents/SAC Scanner` does
not exist on Windows and should not be expected to transfer.

Codex should read `AGENTS.md` from the repository root after this file is pulled.
