package commands

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newGetCmd() *cobra.Command {
	var field string

	cmd := &cobra.Command{
		Use:   "get <name>",
		Short: "Read and decrypt a secret",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return withSession(func(sess *app.Session) error {
				var pin string
				var err error
				if sess.NeedsPIN() {
					if pin, err = promptHidden(cmd, "PIN: "); err != nil {
						return err
					}
				}

				val, err := sess.Get(args[0], pin, field)
				if err != nil {
					return err
				}

				fmt.Fprintln(cmd.OutOrStdout(), string(val))
				return nil
			})
		},
	}

	cmd.Flags().StringVar(&field, "field", "", "print a single field from the secret JSON (default: value)")
	return cmd
}
