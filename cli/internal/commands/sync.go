package commands

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newSyncCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "sync",
		Short: "Synchronize secrets with the configured remote",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return withSession(func(sess *app.Session) error {
				pin, err := pinIfNeeded(cmd, sess)
				if err != nil {
					return err
				}

				res, err := sess.Sync(cmd.Context(), pin)
				if err != nil {
					return err
				}

				out := cmd.OutOrStdout()
				fmt.Fprintf(out, "Synced: %d pulled, %d pushed", res.Pulled, res.Pushed)
				if res.Reshared > 0 {
					fmt.Fprintf(out, ", %d reshared", res.Reshared)
				}
				if res.Conflicts > 0 {
					fmt.Fprintf(out, ", %d conflicts (re-run sync to reconcile)", res.Conflicts)
				}
				fmt.Fprintln(out)
				return nil
			})
		},
	}
}
