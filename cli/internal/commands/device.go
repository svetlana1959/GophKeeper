package commands

import (
	"crypto/sha256"
	"fmt"
	"text/tabwriter"
	"time"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newDeviceCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "device",
		Short: "Manage the devices linked to your account",
	}
	cmd.AddCommand(
		newDeviceInviteCmd(),
		newDeviceLsCmd(),
		newDeviceRevokeCmd(),
		newDeviceApproveCmd(),
	)
	return cmd
}

// fingerprint is a short, human-comparable code derived from a device's public
// key. The browser shows the same code so the user can confirm they're approving
// the right device.
func fingerprint(publicKey string) string {
	h := sha256.Sum256([]byte(publicKey))
	return fmt.Sprintf("%02x%02x·%02x%02x", h[0], h[1], h[2], h[3])
}

func newDeviceApproveCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "approve <device-id|name>",
		Short: "Approve a device (e.g. a browser) so it can decrypt your secrets",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return withSession(func(sess *app.Session) error {
				pin, err := pinIfNeeded(cmd, sess)
				if err != nil {
					return err
				}
				dev, err := sess.FindDevice(cmd.Context(), pin, args[0])
				if err != nil {
					return err
				}
				ok, err := confirm(cmd, fmt.Sprintf(
					"Approve %q (fingerprint %s)?", dev.Name, fingerprint(dev.PublicKey)))
				if err != nil {
					return err
				}
				if !ok {
					fmt.Fprintln(cmd.OutOrStdout(), "Cancelled.")
					return nil
				}
				if _, err := sess.ApproveDevice(cmd.Context(), pin, dev.ID); err != nil {
					return err
				}
				fmt.Fprintf(cmd.OutOrStdout(),
					"Approved %q — it can now decrypt your secrets.\n", dev.Name)
				return nil
			})
		},
	}
}

func newDeviceRevokeCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "revoke <device-id|name>",
		Short: "Revoke a device you introduced (and everything it introduced)",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return withSession(func(sess *app.Session) error {
				pin, err := pinIfNeeded(cmd, sess)
				if err != nil {
					return err
				}
				if err := sess.RevokeDevice(cmd.Context(), pin, args[0]); err != nil {
					return err
				}
				fmt.Fprintln(cmd.OutOrStdout(),
					"Revoked. Run 'goph sync' to rotate secrets so the device loses access.")
				return nil
			})
		},
	}
}

func newDeviceInviteCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "invite",
		Short: "Create a pairing code to link a new device",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return withSession(func(sess *app.Session) error {
				pin, err := pinIfNeeded(cmd, sess)
				if err != nil {
					return err
				}
				inv, err := sess.CreateInvite(cmd.Context(), pin)
				if err != nil {
					return err
				}
				out := cmd.OutOrStdout()
				fmt.Fprintln(out, "Run this on the new device:")
				fmt.Fprintf(out, "  goph link %s\n", inv.Code)
				fmt.Fprintf(out, "Expires %s\n", inv.ExpiresAt.Local().Format(time.RFC1123))
				return nil
			})
		},
	}
}

func newDeviceLsCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "ls",
		Short: "List the devices linked to your account",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return withSession(func(sess *app.Session) error {
				pin, err := pinIfNeeded(cmd, sess)
				if err != nil {
					return err
				}
				devices, err := sess.ListDevices(cmd.Context(), pin)
				if err != nil {
					return err
				}

				tw := tabwriter.NewWriter(cmd.OutOrStdout(), 0, 0, 2, ' ', 0)
				fmt.Fprintln(tw, "ID\tNAME\tSTATUS\tKEY")
				for _, d := range devices {
					name := d.Name
					if d.This {
						name += " (this device)"
					}
					fmt.Fprintf(tw, "%s\t%s\t%s\t%s\n", d.ID, name, d.Status, shortKey(d.PublicKey))
				}
				return tw.Flush()
			})
		},
	}
}

// shortKey trims an age public key for display.
func shortKey(key string) string {
	if len(key) <= 20 {
		return key
	}
	return key[:20] + "…"
}
