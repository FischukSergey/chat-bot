package tools

import (
	"cmp"
	"context"
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

type summaryIn struct {
	Year         *int    `json:"year"`
	ArticleCode  *string `json:"article_code"`
	ArticleName  *string `json:"article_name"`
	MatchKey     *string `json:"match_key"`
	ExpenseKind  *string `json:"expense_kind"`
	GroupByLevel *int    `json:"group_by_level"`
	Limit        *int    `json:"limit"`
}

func (h *Handler) budgetSummary(ctx context.Context, raw json.RawMessage) (SummaryResult, error) {
	var in summaryIn
	if err := decodeStrict(raw, &in); err != nil {
		return SummaryResult{}, err
	}
	kind, err := normalizeKind(in.ExpenseKind)
	if err != nil {
		return SummaryResult{}, err
	}
	code := deref(in.ArticleCode)
	name := deref(in.ArticleName)
	match := deref(in.MatchKey)
	if in.Year == nil && code == "" && name == "" && match == "" && kind == "" {
		return SummaryResult{}, validationError("нужен year или указатель ветки (article_code / article_name / match_key / expense_kind)")
	}
	if in.GroupByLevel != nil && (*in.GroupByLevel < 1 || *in.GroupByLevel > 5) {
		return SummaryResult{}, validationError("group_by_level должен быть 1…5")
	}
	rowLimit, err := clampLimit(in.Limit, 1, 50, 20)
	if err != nil {
		return SummaryResult{}, err
	}
	// article_code любого уровня — фильтр ancestor_codes (лист содержит сам себя).
	qf := qdrant.BuildFilter(qdrant.BudgetFilter{
		Year:         in.Year,
		ExpenseKind:  kind,
		MatchKey:     match,
		AncestorCode: code,
	})
	points, err := h.qd.ScrollAll(ctx, h.cfg.Collection, qf, 128)
	if err != nil {
		return SummaryResult{}, err
	}
	if name != "" {
		filtered := points[:0]
		for _, p := range points {
			if pathHasName(p.Payload, name) {
				filtered = append(filtered, p)
			}
		}
		points = filtered
	}
	monies := make([]MoneyFields, 0, len(points))
	for _, p := range points {
		monies = append(monies, moneyFromPayload(p.Payload))
	}
	var rows []SummaryRow
	if in.GroupByLevel != nil {
		rows = groupByLevel(points, *in.GroupByLevel)
	} else {
		rows = leafRows(points)
	}
	need := len(rows) > rowLimit
	if need {
		rows = rows[:rowLimit]
	}
	if rows == nil {
		rows = []SummaryRow{}
	}
	return SummaryResult{
		Filter:     in.filterView(kind, code, name, match),
		Total:      sumMoney(monies),
		Rows:       rows,
		NeedRefine: need,
	}, nil
}

func (in summaryIn) filterView(kind, code, name, match string) map[string]any {
	out := map[string]any{}
	if in.Year != nil {
		out["year"] = *in.Year
	}
	if code != "" {
		out["article_code"] = code
	}
	if name != "" {
		out["article_name"] = name
	}
	if match != "" {
		out["match_key"] = match
	}
	if kind != "" {
		out["expense_kind"] = kind
	}
	if in.GroupByLevel != nil {
		out["group_by_level"] = *in.GroupByLevel
	}
	return out
}

func leafRows(points []qdrant.Point) []SummaryRow {
	rows := make([]SummaryRow, 0, len(points))
	for _, p := range points {
		level := 0
		if n := payloadInt(p.Payload, "article_level"); n != nil {
			level = *n
		}
		rows = append(rows, SummaryRow{
			Code:        payloadString(p.Payload, "article_code", ""),
			Name:        payloadString(p.Payload, "article_name", ""),
			Level:       level,
			MoneyFields: moneyFromPayload(p.Payload),
		})
	}
	sortRows(rows)
	return rows
}

func groupByLevel(points []qdrant.Point, level int) []SummaryRow {
	type acc struct {
		name   string
		level  int
		monies []MoneyFields
	}
	groups := map[string]*acc{}
	order := []string{}
	for _, p := range points {
		code, name, lvl := groupKey(p.Payload, level)
		if code == "" {
			continue
		}
		g, ok := groups[code]
		if !ok {
			g = &acc{name: name, level: lvl}
			groups[code] = g
			order = append(order, code)
		}
		g.monies = append(g.monies, moneyFromPayload(p.Payload))
	}
	rows := make([]SummaryRow, 0, len(order))
	for _, code := range order {
		g := groups[code]
		rows = append(rows, SummaryRow{
			Code:        code,
			Name:        g.name,
			Level:       g.level,
			MoneyFields: sumMoney(g.monies),
		})
	}
	sortRows(rows)
	return rows
}

func groupKey(p map[string]any, level int) (code, name string, outLevel int) {
	code = payloadString(p, fmt.Sprintf("l%d_code", level), "")
	name = payloadString(p, fmt.Sprintf("l%d_name", level), "")
	if code != "" {
		return code, name, level
	}
	code = payloadString(p, "article_code", "")
	name = payloadString(p, "article_name", "")
	outLevel = 0
	if n := payloadInt(p, "article_level"); n != nil {
		outLevel = *n
	}
	return code, name, outLevel
}

func sortRows(rows []SummaryRow) {
	slices.SortFunc(rows, func(a, b SummaryRow) int {
		switch {
		case a.Limit == nil && b.Limit == nil:
			return strings.Compare(a.Code, b.Code)
		case a.Limit == nil:
			return 1
		case b.Limit == nil:
			return -1
		default:
			if c := cmp.Compare(*b.Limit, *a.Limit); c != 0 {
				return c
			}
			return strings.Compare(a.Code, b.Code)
		}
	})
}
