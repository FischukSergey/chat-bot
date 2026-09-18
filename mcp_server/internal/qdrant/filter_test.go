package qdrant

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestBuildFilterEmpty(t *testing.T) {
	if BuildFilter(BudgetFilter{}) != nil {
		t.Fatal("пустой фильтр должен быть nil")
	}
}

func TestBuildFilterAncestorOnly(t *testing.T) {
	f := BuildFilter(BudgetFilter{AncestorCode: "production:1.8"})
	if f == nil || len(f.Must) != 1 || f.Must[0].Key != "ancestor_codes" {
		t.Fatalf("%+v", f)
	}
}

func TestBuildFilterFields(t *testing.T) {
	year := 2026
	minV, maxV := 10.0, 20.0
	f := BuildFilter(BudgetFilter{
		Year:         &year,
		ExpenseKind:  "production",
		ArticleCode:  "production:1.8.2",
		AncestorCode: "production:1.8",
		AmountMin:    &minV,
		AmountMax:    &maxV,
	})
	if f == nil || len(f.Must) != 5 {
		t.Fatalf("must=%v", f)
	}
	raw, err := json.Marshal(f)
	if err != nil {
		t.Fatal(err)
	}
	s := string(raw)
	for _, want := range []string{
		`"year"`, `"production"`, `"ancestor_codes"`, `"limit_amount"`, `"gte"`, `"lte"`,
	} {
		if !strings.Contains(s, want) {
			t.Fatalf("в JSON нет %s: %s", want, s)
		}
	}
}
