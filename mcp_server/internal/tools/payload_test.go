package tools

import "testing"

func TestPathHasNameContainsParent(t *testing.T) {
	p := map[string]any{
		"article_name": "газопроводы АО Газпром",
		"l3_name":      "аренда газопроводов, в т.ч.",
		"l2_name":      "аренда",
		"ancestor_names": []any{
			"прочие расходы",
			"аренда",
			"аренда газопроводов, в т.ч.",
		},
	}
	if !pathHasName(p, "аренда газопроводов") {
		t.Fatal("фраза родителя должна находить лист")
	}
	if !pathHasName(p, "Аренда газопроводов, в т.ч.") {
		t.Fatal("нормализация регистра и пунктуации")
	}
	if !pathHasName(p, "газопроводы АО Газпром") {
		t.Fatal("точное имя листа")
	}
	if pathHasName(p, "вода") {
		t.Fatal("короткое чужое имя не должно матчиться")
	}
}

func TestNormalizeName(t *testing.T) {
	if got := normalizeName("  Аренда  газопроводов, в т.ч. "); got != "аренда газопроводов, в т.ч" {
		t.Fatalf("%q", got)
	}
}
