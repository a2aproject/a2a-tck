// runner is the Go reference runner for the a2a-jcs-v01 corpus, validating
// against gowebpki/jcs -- the second, independent implementation the
// corpus was cross-checked against at generation time. Two runners in two
// languages exist so the vectors are demonstrably not encoding one
// implementation's habits.
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

const specCommitPinned = "19598c4" // a2a-protocol.org/A2A commit this corpus's clauses were read from

type vector struct {
	ID          string                 `json:"id"`
	Clause      string                 `json:"clause"`
	Disposition string                 `json:"disposition"`
	Input       map[string]interface{} `json:"input,omitempty"`
	InputRaw    string                 `json:"input_raw,omitempty"`
	Expected    struct {
		CanonicalUTF8Hex string `json:"canonical_utf8_hex"`
	} `json:"expected"`
}

type manifestEntry struct {
	Path string `json:"path"`
}

type manifest struct {
	CorpusDigest string          `json:"corpusDigest"`
	Vectors      []manifestEntry `json:"vectors"`
}

type result struct {
	ID     string `json:"id"`
	Pass   bool   `json:"pass"`
	Detail string `json:"detail"`
}

func stripSignatures(m map[string]interface{}) map[string]interface{} {
	out := make(map[string]interface{}, len(m))
	for k, v := range m {
		if k == "signatures" {
			continue
		}
		out[k] = v
	}
	return out
}

func checkVector(v vector) (bool, string) {
	if v.Disposition == "MUST-ACCEPT" {
		obj := v.Input
		if v.Clause == "a2a-spec-8.4.1-rule-3" {
			obj = stripSignatures(obj)
		}
		raw, err := json.Marshal(obj)
		if err != nil {
			return false, "could not re-marshal input: " + err.Error()
		}
		out, err := jcs.Transform(raw)
		if err != nil {
			return false, "canonicalization errored, expected success: " + err.Error()
		}
		want, err := hex.DecodeString(v.Expected.CanonicalUTF8Hex)
		if err != nil {
			return false, "bad expected hex in vector file: " + err.Error()
		}
		if string(out) != string(want) {
			return false, fmt.Sprintf("byte mismatch: got %q want %q", out, want)
		}
		return true, "ok"
	}
	// MUST-REJECT
	if v.Clause == "a2a-spec-8.4.1-rule-3" {
		var obj map[string]interface{}
		if err := json.Unmarshal([]byte(v.InputRaw), &obj); err != nil {
			return false, "could not parse input_raw: " + err.Error()
		}
		if _, has := obj["signatures"]; has {
			return true, "correctly detected forbidden 'signatures' key"
		}
		return false, "failed to detect the violation this vector carries"
	}
	if _, err := jcs.Transform([]byte(v.InputRaw)); err != nil {
		return true, "correctly refused: " + err.Error()
	}
	return false, "accepted input that should have been refused"
}

func main() {
	vroot := "vectors"
	if len(os.Args) > 1 {
		vroot = os.Args[1]
	}
	mraw, err := os.ReadFile(filepath.Join(vroot, "MANIFEST.json"))
	if err != nil {
		fmt.Fprintln(os.Stderr, "read manifest:", err)
		os.Exit(2)
	}
	var m manifest
	if err := json.Unmarshal(mraw, &m); err != nil {
		fmt.Fprintln(os.Stderr, "parse manifest:", err)
		os.Exit(2)
	}

	var results []result
	passed := 0
	entries := append([]manifestEntry(nil), m.Vectors...)
	sort.Slice(entries, func(i, j int) bool { return entries[i].Path < entries[j].Path })
	for _, e := range entries {
		raw, err := os.ReadFile(filepath.Join(vroot, e.Path))
		if err != nil {
			fmt.Fprintln(os.Stderr, "read vector:", e.Path, err)
			os.Exit(2)
		}
		var v vector
		if err := json.Unmarshal(raw, &v); err != nil {
			fmt.Fprintln(os.Stderr, "parse vector:", e.Path, err)
			os.Exit(2)
		}
		ok, detail := checkVector(v)
		if ok {
			passed++
		}
		results = append(results, result{ID: v.ID, Pass: ok, Detail: detail})
	}

	record := map[string]interface{}{
		"runner":       "go/gowebpki-jcs",
		"corpusDigest": m.CorpusDigest,
		"specCommit":   specCommitPinned,
		"coverage": map[string]int{
			"total": len(results), "passed": passed, "failed": len(results) - passed,
		},
		"results": results,
	}
	out, _ := json.MarshalIndent(record, "", "  ")
	fmt.Println(string(out))
	if passed != len(results) {
		os.Exit(1)
	}
}
