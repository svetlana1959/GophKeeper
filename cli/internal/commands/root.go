// Package commands defines the goph CLI command tree.
//
// Only the root command exists so far — feature commands (init, set, get,
// list, delete, push, pull, device ...) will be added under their own issues.
// Commands orchestrate the domain and infrastructure; they hold no business
// logic themselves.
package commands

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

// version is the CLI version; override at build time with
// -ldflags "-X github.com/svetlana1959/GophKeeper/cli/internal/commands.version=x.y.z".
var version = "dev"

// newRootCmd builds the top-level `goph` command.
// Check cobra for license, it is AI generated code...
// Couldn't be bothered to check....
func newRootCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "goph",
		Short: "GophKeeper — zero-knowledge, distributed secret manager",
		Long: `GophKeeper is a zero-knowledge cloud secret manager with distributed
client-side encryption based on age.

This is a scaffold: no feature commands are implemented yet.`,
		Version:       version,
		SilenceUsage:  true,
		SilenceErrors: true,
	}
}

// Execute runs the root command and exits non-zero on error.
func Execute() {
	if err := newRootCmd().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
