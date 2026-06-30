package commands

import (
	"encoding/json"
	"fmt"
	"text/tabwriter"
	"time"

	"github.com/spf13/cobra"

	"github.com/svetlana1959/GophKeeper/cli/internal/app"
)

func newListCmd() *cobra.Command {
	var (
		all    bool
		folder string
		asJSON bool
	)

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List stored secrets (metadata only, no decryption)",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return withSession(func(sess *app.Session) error {
				items, err := sess.List(folder, all)
				if err != nil {
					return err
				}

				out := cmd.OutOrStdout()
				if asJSON {
					enc := json.NewEncoder(out)
					enc.SetIndent("", "  ")
					return enc.Encode(items)
				}
				if len(items) == 0 {
					fmt.Fprintln(out, "No secrets yet")
					return nil
				}

				tw := tabwriter.NewWriter(out, 0, 2, 2, ' ', 0)
				fmt.Fprintln(tw, "NAME\tFOLDER\tVERSION\tUPDATED\tSTATUS")
				for _, it := range items {
					status := "active"
					if it.Deleted {
						status = "deleted"
					}
					fmt.Fprintf(tw, "%s\t%s\t%d\t%s\t%s\n",
						it.Name, it.Folder, it.Version, it.UpdatedAt.Format(time.RFC3339), status)
				}
				return tw.Flush()
			})
		},
	}

	cmd.Flags().BoolVar(&all, "all", false, "include soft-deleted secrets")
	cmd.Flags().StringVar(&folder, "folder", "", "filter by folder")
	cmd.Flags().BoolVar(&asJSON, "json", false, "output JSON")
	return cmd
}
