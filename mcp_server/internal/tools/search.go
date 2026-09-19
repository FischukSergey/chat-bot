package tools

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

type searchIn struct {
	Query       *string   `json:"query"`
	Collections []string  `json:"collections"`
	Filters     *filterIn `json:"filters"`
	Limit       *int      `json:"limit"`
}

type filterIn struct {
	Year         *int     `json:"year"`
	ExpenseKind  *string  `json:"expense_kind"`
	ArticleCode  *string  `json:"article_code"`
	ArticleName  *string  `json:"article_name"`
	MatchKey     *string  `json:"match_key"`
	AncestorCode *string  `json:"ancestor_code"`
	AmountMin    *float64 `json:"amount_min"`
	AmountMax    *float64 `json:"amount_max"`
}

func (h *Handler) searchRecords(ctx context.Context, raw json.RawMessage) (SearchResult, error) {
	var in searchIn
	if err := decodeStrict(raw, &in); err != nil {
		return SearchResult{}, err
	}
	cols := in.Collections
	if cols == nil {
		cols = []string{h.cfg.Collection}
	}
	if len(cols) == 0 {
		return SearchResult{}, validationError("collections: минимум одна коллекция")
	}
	for _, c := range cols {
		if c != "budget_items" {
			return SearchResult{}, validationError("коллекция %q недоступна, только budget_items", c)
		}
	}
	limit, err := clampLimit(in.Limit, h.cfg.LimitMin, h.cfg.LimitMax, h.cfg.LimitDefault)
	if err != nil {
		return SearchResult{}, err
	}
	qf, err := in.Filters.qdrantFilter()
	if err != nil {
		return SearchResult{}, err
	}
	name := ""
	if in.Filters != nil {
		name = deref(in.Filters.ArticleName)
	}
	query := ""
	if in.Query != nil {
		query = strings.TrimSpace(*in.Query)
	}
	if query == "" {
		var points []qdrant.Point
		if name != "" {
			all, err := h.qd.ScrollAll(ctx, h.cfg.Collection, qf, 128)
			if err != nil {
				return SearchResult{}, err
			}
			points = takePoints(filterPointsByName(all, name), limit)
		} else {
			res, err := h.qd.Scroll(ctx, h.cfg.Collection, qdrant.ScrollRequest{Filter: qf, Limit: limit})
			if err != nil {
				return SearchResult{}, err
			}
			points = res.Points
		}
		hits := make([]Hit, 0, len(points))
		for _, p := range points {
			hits = append(hits, hitFromPoint(h.cfg.Collection, p, false))
		}
		return SearchResult{Hits: hits}, nil
	}
	vecs, err := h.emb.Embed(ctx, []string{query})
	if err != nil {
		return SearchResult{}, err
	}
	if len(vecs) != 1 {
		return SearchResult{}, validationError("embeddings не вернули вектор")
	}
	searchLimit := limit
	if name != "" {
		searchLimit = max(limit, h.cfg.LimitMax)
	}
	found, err := h.qd.Search(ctx, h.cfg.Collection, qdrant.SearchRequest{
		Vector:         vecs[0],
		Filter:         qf,
		Limit:          searchLimit,
		ScoreThreshold: h.cfg.ScoreThreshold,
	})
	if err != nil {
		return SearchResult{}, err
	}
	found = takePoints(filterPointsByName(found, name), limit)
	hits := make([]Hit, 0, len(found))
	for _, p := range found {
		hits = append(hits, hitFromPoint(h.cfg.Collection, p, true))
	}
	return SearchResult{Hits: hits}, nil
}

func (f *filterIn) qdrantFilter() (*qdrant.Filter, error) {
	if f == nil {
		return nil, nil
	}
	kind, err := normalizeKind(f.ExpenseKind)
	if err != nil {
		return nil, err
	}
	// article_name — не exact в Qdrant: родитель есть только у листьев в l1…l5.
	return qdrant.BuildFilter(qdrant.BudgetFilter{
		Year:         f.Year,
		ExpenseKind:  kind,
		ArticleCode:  deref(f.ArticleCode),
		MatchKey:     deref(f.MatchKey),
		AncestorCode: deref(f.AncestorCode),
		AmountMin:    f.AmountMin,
		AmountMax:    f.AmountMax,
	}), nil
}

func filterPointsByName(points []qdrant.Point, name string) []qdrant.Point {
	if name == "" {
		return points
	}
	out := make([]qdrant.Point, 0, len(points))
	for _, p := range points {
		if pathHasName(p.Payload, name) {
			out = append(out, p)
		}
	}
	return out
}

func takePoints(points []qdrant.Point, limit int) []qdrant.Point {
	if limit < len(points) {
		return points[:limit]
	}
	return points
}

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return strings.TrimSpace(*s)
}
