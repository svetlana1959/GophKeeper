package commands

import (
	"errors"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newInitCmd() *cobra.Command {
	var (
		deviceName string
		keyFile    string
		usePIN     bool
		force      bool
	)

	cmd := &cobra.Command{
		Use:   "init",
		Short: "Set up this device: identity, config, and local vault",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			if deviceName == "" {
				if host, err := os.Hostname(); err == nil {
					deviceName = host
				}
			}

			var privateKey string
			if keyFile != "" {
				data, err := os.ReadFile(keyFile)
				if err != nil {
					return fmt.Errorf("read key file: %w", err)
				}
				privateKey = strings.TrimSpace(string(data))
			}

			pin, err := readNewPIN(cmd, usePIN)
			if err != nil {
				return err
			}

			res, err := app.Init(app.InitParams{
				DeviceName: deviceName,
				PIN:        pin,
				PrivateKey: privateKey,
				Force:      force,
			})
			if err != nil {
				return err
			}

			out := cmd.OutOrStdout()
			fmt.Fprintf(out, "Initialized device %q\n", deviceName)
			fmt.Fprintf(out, "Device ID:  %s\n", res.DeviceID)
			fmt.Fprintf(out, "Public key: %s\n", res.PublicKey)
			fmt.Fprintln(out, "\nShare the device ID and public key to enroll this device.")
			return nil
		},
	}

	cmd.Flags().StringVar(&deviceName, "device-name", "", "device name (default: hostname)")
	cmd.Flags().StringVar(&keyFile, "key-file", "", "import an existing age private key from a file")
	cmd.Flags().BoolVar(&usePIN, "pin", false, "protect the private key at rest with a PIN")
	cmd.Flags().BoolVar(&force, "force", false, "overwrite an existing setup")
	return cmd
}

// readNewPIN prompts for a PIN twice and checks they match. Returns "" when no
// PIN was requested.
func readNewPIN(cmd *cobra.Command, usePIN bool) (string, error) {
	if !usePIN {
		return "", nil
	}
	pin, err := promptHidden(cmd, "PIN: ")
	if err != nil {
		return "", err
	}
	confirm, err := promptHidden(cmd, "Confirm PIN: ")
	if err != nil {
		return "", err
	}
	if pin != confirm {
		return "", errors.New("PINs do not match")
	}
	if pin == "" {
		return "", errors.New("PIN must not be empty")
	}
	return pin, nil
}
