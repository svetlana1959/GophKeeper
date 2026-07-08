package commands

import (
	"bytes"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/spf13/cobra"
	"golang.org/x/term"
)

// terminalFd returns the input's file descriptor when it is an interactive
// terminal. Both the echo-off read and the "is it piped?" check go through here,
// so they always agree on the same stream.
func terminalFd(r io.Reader) (int, bool) {
	f, ok := r.(*os.File)
	if !ok {
		return 0, false
	}
	fd := int(f.Fd())
	return fd, term.IsTerminal(fd)
}

// promptHidden reads a line from the command's input. On a terminal it disables
// echo (for PINs); otherwise it reads a plain line so piped input still works.
func promptHidden(cmd *cobra.Command, label string) (string, error) {
	in := cmd.InOrStdin()
	if fd, ok := terminalFd(in); ok {
		fmt.Fprint(cmd.OutOrStdout(), label)
		b, err := term.ReadPassword(fd)
		fmt.Fprintln(cmd.OutOrStdout())
		return string(b), err
	}
	return readLine(in)
}

// readLine reads a single line, consuming exactly up to and including the first
// newline. It reads byte-by-byte rather than buffering ahead, so a command that
// prompts more than once (e.g. init's PIN + confirmation) reads piped input
// line-by-line instead of losing the rest to a buffered reader.
func readLine(r io.Reader) (string, error) {
	var sb strings.Builder
	buf := make([]byte, 1)
	for {
		n, err := r.Read(buf)
		if n > 0 {
			if buf[0] == '\n' {
				break
			}
			if buf[0] != '\r' {
				sb.WriteByte(buf[0])
			}
		}
		if err != nil {
			if err == io.EOF {
				break
			}
			return "", err
		}
	}
	return sb.String(), nil
}

// confirm asks a yes/no question, defaulting to no.
func confirm(cmd *cobra.Command, question string) (bool, error) {
	fmt.Fprintf(cmd.OutOrStdout(), "%s [y/N] ", question)
	line, err := readLine(cmd.InOrStdin())
	if err != nil {
		return false, err
	}
	switch strings.ToLower(strings.TrimSpace(line)) {
	case "y", "yes":
		return true, nil
	default:
		return false, nil
	}
}

// readValue resolves a secret value from --value, --file, piped stdin, or a
// hidden prompt, in that order. Flag presence is checked with Changed so an
// explicit empty --value is honored. A single trailing newline is stripped from
// piped stdin (so `echo secret | goph set` does the obvious thing); --file is
// stored exactly as written.
func readValue(cmd *cobra.Command, value, file string) ([]byte, error) {
	flags := cmd.Flags()
	switch {
	case flags.Changed("value"):
		return []byte(value), nil
	case flags.Changed("file"):
		return os.ReadFile(file)
	}

	in := cmd.InOrStdin()
	if _, ok := terminalFd(in); ok {
		v, err := promptHidden(cmd, "Value: ")
		return []byte(v), err
	}

	data, err := io.ReadAll(in)
	if err != nil {
		return nil, err
	}
	return bytes.TrimSuffix(bytes.TrimSuffix(data, []byte("\n")), []byte("\r")), nil
}
