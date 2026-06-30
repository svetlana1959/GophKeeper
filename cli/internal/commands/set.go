package commands

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newSetCmd() *cobra.Command {
	var (
		value       string
		file        string
		description string
		folder      string
	)

	cmd := &cobra.Command{
		Use:   "set <name>",
		Short: "Create or update a secret",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			val, err := readValue(cmd, value, file)
			if err != nil {
				return err
			}

			return withSession(func(sess *app.Session) error {
				if err := sess.Set(app.SetParams{
					Name:        args[0],
					Value:       val,
					Description: description,
					Folder:      folder,
				}); err != nil {
					return err
				}
				fmt.Fprintf(cmd.OutOrStdout(), "Stored %q\n", args[0])
				return nil
			})
		},
	}

	cmd.Flags().StringVar(&value, "value", "", "secret value (else --file, stdin, or prompt)")
	cmd.Flags().StringVar(&file, "file", "", "read the value from a file")
	cmd.Flags().StringVar(&description, "description", "", "optional description")
	cmd.Flags().StringVar(&folder, "folder", "", "optional folder")
	return cmd
}
