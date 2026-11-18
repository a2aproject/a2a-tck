// runner is the Go reference runner for the a2a-jcs-v01 corpus, validating
// against gowebpki/jcs -- the second, independent implementation the
// corpus was cross-checked against at generation time. Two runners in two
// languages exist so the vectors are demonstrably not encoding one
// implementation's habits.
//
// The corpus tests two functions, named under "targets" in MANIFEST.json: an
// RFC 8785 primitive ("rfc8785", the RFC 8785 vectors) and the bytes an Agent
// Card signature covers ("card-signing-input", every vector). The record this
// runner prints has the same shape as run_python.py's, one tally per target
// and one outcome per vector: pass, diverged (wrong bytes on a MUST-ACCEPT
// vector), refused (an error on a MUST-ACCEPT vector), accepted (bytes for a
// MUST-REJECT vector) or errored (the runner could not ask the implementation).
package main

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"github.com/gowebpki/jcs"
)

const (
	specCommitPinned          = "19598c4" // a2a-protocol.org/A2A commit this corpus's clauses were read from
	signaturesExclusionClause = "a2a-spec-8.4.1-rule-3"
)

var (
	targetOrder = []string{"rfc8785", "card-signing-input"}
	outcomes    = []string{"pass", "diverged", "refused", "accepted", "errored"}
)

type vector struct {
	ID          string          `json:"id"`
	Clause      string          `json:"clause"`
	Disposition string          `json:"disposition"`
	Input       json.RawMessage `json:"input,omitempty"`
	InputRaw    string          `json:"input_raw,omitempty"`
	Expected    struct {
		CanonicalUTF8Hex string `json:"canonical_utf8_hex"`
	} `json:"expected"`
}

type manifestEntry struct {
	Path string `json:"path"`
}

type target struct {
	Function string   `json:"function"`
	Clauses  []string `json:"clauses"`
	Vectors  int      `json:"vectors"`
}

type manifest struct {
	CorpusDigest string            `json:"corpusDigest"`
	Targets      map[string]target `json:"targets"`
	Vectors      []manifestEntry   `json:"vectors"`
}

type result struct {
	Target  string `json:"target"`
	ID      string `json:"id"`
	Outcome string `json:"outcome"`
	Detail  string `json:"detail"`
}

type tally struct {
	Vectors  int            `json:"vectors"`
	Passed   int            `json:"passed"`
	Failed   int            `json:"failed"`
	Outcomes map[string]int `json:"outcomes"`
}

// canonicalize is the RFC 8785 primitive under test: gowebpki/jcs over the
// JSON text of one value.
func canonicalize(raw []byte) ([]byte, error) {
	return jcs.Transform(raw)
}

// signingBytes returns the bytes a card signature covers: drop `signatures`
// (rule 3), then RFC 8785. The card is canonicalized before the field is
// dropped because encoding/json decodes a lone surrogate in an object key to
// U+FFFD without an error; canonical output is well-formed UTF-8, so decoding
// it loses nothing, and the second pass restores RFC 8785 order and escaping.
func signingBytes(raw []byte) ([]byte, error) {
	canonical, err := jcs.Transform(raw)
	if err != nil {
		return nil, err
	}
	var card map[string]json.RawMessage
	if err := json.Unmarshal(canonical, &card); err != nil {
		return nil, err
	}
	delete(card, "signatures")
	stripped, err := json.Marshal(card)
	if err != nil {
		return nil, err
	}
	return jcs.Transform(stripped)
}

func checkVector(v vector, fn func([]byte) ([]byte, error)) (string, string) {
	if v.Disposition == "MUST-ACCEPT" {
		out, err := fn(v.Input)
		if err != nil {
			return "refused", err.Error()
		}
		want, err := hex.DecodeString(v.Expected.CanonicalUTF8Hex)
		if err != nil {
			return "errored", "bad expected hex in vector file: " + err.Error()
		}
		if string(out) != string(want) {
			return "diverged", fmt.Sprintf("got %q want %q", out, want)
		}
		return "pass", "ok"
	}
	// MUST-REJECT
	out, err := fn([]byte(v.InputRaw))
	if v.Clause == signaturesExclusionClause {
		// The input is presented AS a card's signing bytes while still carrying
		// `signatures`. A verifier recomputes the signing bytes from the card and
		// refuses when they differ, so this runs the implementation; a check on
		// the fixture alone would pass whatever it did.
		if err != nil {
			return "refused", "signing path errored on a well-formed card: " + err.Error()
		}
		if string(out) != v.InputRaw {
			return "pass", "refused: not this card's signing bytes"
		}
		return "accepted", "recomputed signing bytes equal bytes that still carry 'signatures'"
	}
	if err != nil {
		return "pass", "refused: " + err.Error()
	}
	return "accepted", fmt.Sprintf("produced %q for input with no canonical form", out)
}

func fail(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "runner: "+format+"\n", args...)
	os.Exit(2)
}

func main() {
	vroot := "vectors"
	if len(os.Args) > 1 {
		vroot = os.Args[1]
	}
	mraw, err := os.ReadFile(filepath.Join(vroot, "MANIFEST.json"))
	if err != nil {
		fail("read manifest: %v", err)
	}
	var m manifest
	if err := json.Unmarshal(mraw, &m); err != nil {
		fail("parse manifest: %v", err)
	}
	if len(m.Targets) != len(targetOrder) {
		fail("manifest declares %d targets, this runner knows %v", len(m.Targets), targetOrder)
	}

	entries := append([]manifestEntry(nil), m.Vectors...)
	sort.Slice(entries, func(i, j int) bool { return entries[i].Path < entries[j].Path })
	var vectors []vector
	for _, e := range entries {
		raw, err := os.ReadFile(filepath.Join(vroot, e.Path))
		if err != nil {
			fail("read vector %s: %v", e.Path, err)
		}
		var v vector
		if err := json.Unmarshal(raw, &v); err != nil {
			fail("parse vector %s: %v", e.Path, err)
		}
		vectors = append(vectors, v)
	}

	functions := map[string]func([]byte) ([]byte, error){
		"rfc8785":            canonicalize,
		"card-signing-input": signingBytes,
	}
	targets := map[string]tally{}
	var results []result
	failed := 0
	for _, name := range targetOrder {
		t, ok := m.Targets[name]
		if !ok {
			fail("manifest declares no target %q", name)
		}
		owns := map[string]bool{}
		for _, c := range t.Clauses {
			owns[c] = true
		}
		counts := map[string]int{}
		for _, o := range outcomes {
			counts[o] = 0
		}
		n := 0
		for _, v := range vectors {
			if !owns[v.Clause] {
				continue
			}
			n++
			outcome, detail := checkVector(v, functions[name])
			counts[outcome]++
			results = append(results, result{Target: name, ID: v.ID, Outcome: outcome, Detail: detail})
		}
		if n != t.Vectors {
			fail("%s: manifest says %d vectors, found %d", name, t.Vectors, n)
		}
		targets[name] = tally{Vectors: n, Passed: counts["pass"], Failed: n - counts["pass"], Outcomes: counts}
		failed += n - counts["pass"]
	}

	record := map[string]interface{}{
		"runner": "go/gowebpki-jcs",
		"implementation": map[string]string{
			"rfc8785":            "github.com/gowebpki/jcs Transform",
			"card-signing-input": "reference: drop signatures, then github.com/gowebpki/jcs Transform",
		},
		"corpusDigest":  m.CorpusDigest,
		"specCommit":    specCommitPinned,
		"targets":       targets,
		"targetsNotRun": map[string]string{},
		"results":       results,
	}
	out, err := json.MarshalIndent(record, "", "  ")
	if err != nil {
		fail("encode record: %v", err)
	}
	fmt.Println(string(out))
	if failed != 0 {
		os.Exit(1)
	}
}
