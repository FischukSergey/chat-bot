package tools

import (
	"encoding/json"
	"strconv"
	"strings"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

func payloadString(p map[string]any, key, fallback string) string {
	if p == nil {
		return fallback
	}
	v, ok := p[key]
	if !ok || v == nil {
		return fallback
	}
	switch t := v.(type) {
	case string:
		return t
	default:
		return fallback
	}
}

func payloadFloat(p map[string]any, key string) *float64 {
	if p == nil {
		return nil
	}
	v, ok := p[key]
	if !ok || v == nil {
		return nil
	}
	switch t := v.(type) {
	case float64:
		return &t
	case json.Number:
		f, err := t.Float64()
		if err != nil {
			return nil
		}
		return &f
	case int:
		f := float64(t)
		return &f
	default:
		return nil
	}
}

func payloadInt(p map[string]any, key string) *int {
	if p == nil {
		return nil
	}
	v, ok := p[key]
	if !ok || v == nil {
		return nil
	}
	switch t := v.(type) {
	case float64:
		n := int(t)
		return &n
	case json.Number:
		i, err := t.Int64()
		if err != nil {
			return nil
		}
		n := int(i)
		return &n
	case int:
		return &t
	case string:
		n, err := strconv.Atoi(t)
		if err != nil {
			return nil
		}
		return &n
	default:
		return nil
	}
}

func moneyFromPayload(p map[string]any) MoneyFields {
	return MoneyFields{
		Limit:            payloadFloat(p, "limit_amount"),
		Fact:             payloadFloat(p, "fact_amount"),
		Obligation:       payloadFloat(p, "obligation_amount"),
		RemainFree:       payloadFloat(p, "remain_free"),
		RemainUnexecuted: payloadFloat(p, "remain_unexecuted"),
		AmountUnit:       payloadString(p, "amount_unit", "thousand_rub"),
		Currency:         payloadString(p, "currency", "RUB"),
	}
}

func sourceFromPayload(p map[string]any) Source {
	return Source{
		SourceFile: payloadString(p, "source_file", ""),
		Sheet:      payloadString(p, "sheet", ""),
		Row:        payloadInt(p, "row"),
	}
}

func sumMoney(items []MoneyFields) MoneyFields {
	var lim, fact, obl, free, unex []float64
	unit, cur := "thousand_rub", "RUB"
	for _, m := range items {
		if m.AmountUnit != "" {
			unit = m.AmountUnit
		}
		if m.Currency != "" {
			cur = m.Currency
		}
		if m.Limit != nil {
			lim = append(lim, *m.Limit)
		}
		if m.Fact != nil {
			fact = append(fact, *m.Fact)
		}
		if m.Obligation != nil {
			obl = append(obl, *m.Obligation)
		}
		if m.RemainFree != nil {
			free = append(free, *m.RemainFree)
		}
		if m.RemainUnexecuted != nil {
			unex = append(unex, *m.RemainUnexecuted)
		}
	}
	return MoneyFields{
		Limit:            sumOrNil(lim),
		Fact:             sumOrNil(fact),
		Obligation:       sumOrNil(obl),
		RemainFree:       sumOrNil(free),
		RemainUnexecuted: sumOrNil(unex),
		AmountUnit:       unit,
		Currency:         cur,
	}
}

func sumOrNil(xs []float64) *float64 {
	if len(xs) == 0 {
		return nil
	}
	s := 0.0
	for _, x := range xs {
		s += x
	}
	return &s
}

func pickFields(p map[string]any) map[string]any {
	keys := []string{
		"article_code", "article_name", "expense_kind", "year", "match_key",
		"article_level", "ancestor_codes",
		"l1_code", "l1_name", "l2_code", "l2_name", "l3_code", "l3_name",
		"l4_code", "l4_name", "l5_code", "l5_name",
		"limit_amount", "fact_amount", "obligation_amount",
		"remain_free", "remain_free_source", "remain_unexecuted",
		"amount_unit", "currency",
	}
	out := make(map[string]any, len(keys))
	for _, k := range keys {
		if v, ok := p[k]; ok {
			out[k] = v
		}
	}
	return out
}

func pathHasName(p map[string]any, want string) bool {
	if want == "" {
		return true
	}
	for _, k := range []string{"article_name", "l1_name", "l2_name", "l3_name", "l4_name", "l5_name"} {
		if payloadString(p, k, "") == want {
			return true
		}
	}
	return false
}

func hitFromPoint(collection string, p qdrant.Point, withScore bool) Hit {
	h := Hit{
		Collection: collection,
		ID:         string(p.ID),
		Fields:     pickFields(p.Payload),
		Source:     sourceFromPayload(p.Payload),
	}
	if withScore {
		s := p.Score
		h.Score = &s
	}
	return h
}

func clampLimit(v *int, minV, maxV, def int) (int, error) {
	if v == nil {
		return def, nil
	}
	if *v < minV || *v > maxV {
		return 0, validationError("limit должен быть %d…%d", minV, maxV)
	}
	return *v, nil
}

func normalizeKind(v *string) (string, error) {
	if v == nil || strings.TrimSpace(*v) == "" {
		return "", nil
	}
	k := strings.TrimSpace(*v)
	if k != "production" && k != "management" {
		return "", validationError("expense_kind: только production или management")
	}
	return k, nil
}
