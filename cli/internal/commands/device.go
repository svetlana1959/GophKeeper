package commands

import (
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
	cmd.AddCommand(newDeviceInviteCmd(), newDeviceLsCmd())
	return cmd
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
				fmt.Fprintln(tw, "NAME\tSTATUS\tKEY")
				for _, d := range devices {
					name := d.Name
					if d.This {
						name += " (this device)"
					}
					fmt.Fprintf(tw, "%s\t%s\t%s\n", name, d.Status, shortKey(d.PublicKey))
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
