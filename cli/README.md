# goph — GophKeeper CLI

Zero-knowledge, distributed secret manager. Secrets are encrypted client-side
with [age](https://github.com/FiloSottile/age) and stored in a local SQLite
vault; plaintext never touches disk.

![demo](docs/demo.gif)

## Install

### Linux / macOS

```sh
curl -sSL https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.sh | sh
```

Installs to `/usr/local/bin` (uses `sudo` only if needed). Override the location:

```sh
curl -sSL https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.sh | INSTALL_DIR="$HOME/.local/bin" sh
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.ps1 | iex
```

Installs to `%LOCALAPPDATA%\Programs\goph` and adds it to your user `PATH`
(restart the terminal afterwards). Override with `$Env:InstallDir`.

### From a release

Grab the archive for your OS/arch from the
[releases page](https://github.com/svetlana1959/GophKeeper/releases), verify it
against `checksums.txt`, and put `goph` on your `PATH`.

### From source

```sh
cd cli && go build -o goph . && ./goph --version
```

## Usage

```sh
goph init                 # set up this device (identity + local vault)
goph set github --value … # store a secret (also --file, stdin, or prompt)
goph get github           # read and decrypt a secret
goph list                 # list metadata (no decryption)
goph delete github        # soft-delete (tombstone)
```

See [docs/](docs/) for the recorded demo.

## Releasing

Maintainers cut a release with `./release.sh` (bumps + tags + pushes); the
`Release CLI` workflow then cross-compiles every target via
[GoReleaser](https://goreleaser.com) and publishes the archives + checksums.
