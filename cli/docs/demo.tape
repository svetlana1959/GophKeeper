# GophKeeper CLI demo — records the full secret lifecycle.
#
# Render with:
#   go build -o /somewhere/on/PATH/goph .   # from cli/
#   cd cli/docs && vhs demo.tape
#
# `goph` must be on PATH; the tape runs against a throwaway $HOME so it never
# touches your real ~/.goph.

Output demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 800
Set Padding 20
Set TypingSpeed 45ms

# Isolate HOME and use a clean prompt; hidden from the recording.
Hide
Type "export HOME=$(mktemp -d) PS1='$ '" Enter
Type "clear" Enter
Show

Sleep 1s
Type "# 1. Set up this device: age identity + local encrypted vault" Enter
Type "goph init --device-name demo-laptop" Enter
Sleep 2.5s

Type "# 2. Store a couple of secrets (value never echoed to logs)" Enter
Type 'goph set github --value ghp_demo_T0ken --folder work' Enter
Sleep 1s
Type 'goph set email --value hunter2 --description "personal email" --folder home' Enter
Sleep 1.5s

Type "# 3. Read a secret back, decrypted with this device's key" Enter
Type "goph get github" Enter
Sleep 2s

Type "# 4. Pull a single field" Enter
Type "goph get email --field description" Enter
Sleep 2s

Type "# 5. List stored secrets — metadata only, no decryption" Enter
Type "goph list" Enter
Sleep 2.5s

Type "# 6. Soft-delete a secret (tombstone for later sync)" Enter
Type "goph delete github --force" Enter
Sleep 1.5s

Type "# 7. github is gone; --all would still show the tombstone" Enter
Type "goph list" Enter
Sleep 3s
