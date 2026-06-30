// Package config owns the non-secret client configuration (#23): the Config
// model and its rules, the Store port, and the YAML+filesystem adapter
// (FileStore) that implements it. The file lives at $HOME/.goph/config.yaml
// (or %USERPROFILE%\.goph\config.yaml on Windows) and holds non-secret
// settings only, for example:
//
//	remote: https://example.com    # backend API URL used by push/pull
//	secret-db: ~/.goph/secrets.db  # path to the local SQLite secret store
//	device-name: laptop            # human-readable device identity
//	default-folder: personal       # folder new secrets land in by default
package config
