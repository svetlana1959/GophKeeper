package commands

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newLinkCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "link <code>",
		Short: "Link this device to an existing account using a pairing code",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return withSession(func(sess *app.Session) error {
				if err := sess.Link(cmd.Context(), args[0]); err != nil {
					return err
				}
				fmt.Fprintln(cmd.OutOrStdout(), "Linked. Run 'goph sync' to pull your secrets.")
				return nil
			})
		},
	}
}
