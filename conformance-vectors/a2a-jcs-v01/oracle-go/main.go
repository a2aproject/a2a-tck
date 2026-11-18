// jcsoracle reads a JSON value from stdin and writes its RFC 8785 (JCS)
// canonical form to stdout, using gowebpki/jcs directly (the second,
// independent oracle -- do not reimplement canonicalization here).
package main

import (
	"fmt"
	"io"
	"os"

	"github.com/gowebpki/jcs"
)

func main() {
	raw, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "read stdin:", err)
		os.Exit(1)
	}
	out, err := jcs.Transform(raw)
	if err != nil {
		fmt.Fprintln(os.Stderr, "REJECT:", err)
		os.Exit(2)
	}
	os.Stdout.Write(out)
}
