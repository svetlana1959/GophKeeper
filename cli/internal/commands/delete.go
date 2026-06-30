package commands

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newDeleteCmd() *cobra.Command {
	var force bool

	cmd := &cobra.Command{
		Use:   "delete <name>",
		Short: "Soft-delete a secret (tombstone)",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			if !force {
				ok, err := confirm(cmd, fmt.Sprintf("Delete %q?", name))
				if err != nil {
					return err
				}
				if !ok {
					fmt.Fprintln(cmd.OutOrStdout(), "Aborted")
					return nil
				}
			}

			return withSession(func(sess *app.Session) error {
				if err := sess.Delete(name); err != nil {
					return err
				}
				fmt.Fprintf(cmd.OutOrStdout(), "Deleted %q\n", name)
				return nil
			})
		},
	}

	cmd.Flags().BoolVar(&force, "force", false, "skip the confirmation prompt")
	return cmd
}
