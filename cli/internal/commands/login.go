package commands

import (
	"github.com/spf13/cobra"
	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newLoginCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "login <remote> <url>",
		Short: "Log in to a remote secret storage",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			return withSession(func(s *app.Session) error {
				err := s.Login(args[0], args[1])
				if err != nil {
					return err
				}
				return nil
			})
		},
	}

	return cmd
}
