# GophKeeper CLI — demos

![GophKeeper CLI demo](demo.gif)

The demo walks through the full local secret lifecycle:

1. `goph init` — set up the device (age identity + local encrypted vault)
2. `goph set` — store secrets (with `--folder`, `--description`)
3. `goph get` — read a secret back, decrypted with the device key (`--field` for one field)
4. `goph list` — list metadata only, no decryption
5. `goph delete` — soft-delete (tombstone) a secret

## Regenerating

Recorded with [charmbracelet/vhs](https://github.com/charmbracelet/vhs)
(needs `vhs`, `ttyd`, and `ffmpeg`).

```sh
# from the cli/ directory: put goph on PATH
go build -o "$(go env GOPATH)/bin/goph" .

# render the tape (writes demo.gif next to it)
cd docs && vhs demo.tape
```

The tape runs against a throwaway `$HOME`, so it never touches your real
`~/.goph`.
