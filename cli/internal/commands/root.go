// Package commands defines the goph CLI command tree. Commands gather input
// (flags, prompts, stdin) and format output; the orchestration lives in the app
// layer, so commands hold no business logic themselves.
package commands

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

// version is the CLI version; override at build time with
// -ldflags "-X github.com/svetlana1959/GophKeeper/cli/internal/commands.version=x.y.z".
var version = "dev"

// newRootCmd builds the top-level `goph` command and registers its subcommands.
func newRootCmd() *cobra.Command {
	root := &cobra.Command{
		Use:   "goph",
		Short: "GophKeeper — zero-knowledge, distributed secret manager",
		Long: `GophKeeper is a zero-knowledge cloud secret manager with distributed
client-side encryption based on age.`,
		Version:       version,
		SilenceUsage:  true,
		SilenceErrors: true,
	}
	root.AddCommand(
		newInitCmd(),
		newSetCmd(),
		newGetCmd(),
		newDeleteCmd(),
		newListCmd(),
	)
	return root
}

// withSession opens the vault, runs fn against it, and closes it. It centralizes
// the open/close lifecycle so commands don't repeat it.
func withSession(fn func(*app.Session) error) error {
	sess, err := app.Open()
	if err != nil {
		return err
	}
	defer sess.Close()
	return fn(sess)
}

// Execute runs the root command and exits non-zero on error.
func Execute() {
	if err := newRootCmd().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
