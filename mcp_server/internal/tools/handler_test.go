package tools

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

type fakeStore struct {
	points []qdrant.Point
	search []qdrant.Point
}

func (f *fakeStore) Count(context.Context, string, *qdrant.Filter) (int, error) {
	return len(f.points), nil
}

func (f *fakeStore) Scroll(_ context.Context, _ string, req qdrant.ScrollRequest) (qdrant.ScrollResult, error) {
	n := req.Limit
	if n <= 0 || n > len(f.points) {
		n = len(f.points)
	}
	return qdrant.ScrollResult{Points: f.points[:n]}, nil
}

func (f *fakeStore) ScrollAll(context.Context, string, *qdrant.Filter, int) ([]qdrant.Point, error) {
	return f.points, nil
}

func (f *fakeStore) Search(context.Context, string, qdrant.SearchRequest) ([]qdrant.Point, error) {
	return f.search, nil
}

type fakeEmbed struct{}

func (fakeEmbed) Embed(context.Context, []string) ([][]float64, error) {
	return [][]float64{{0.1, 0.2}}, nil
}

func testHandler(points []qdrant.Point) *Handler {
	return New(config.Config{
		Collection:   "budget_items",
		LimitMin:     1,
		LimitMax:     20,
		LimitDefault: 8,
	}, &fakeStore{points: points, search: points}, fakeEmbed{})
}

func TestUnknownTool(t *testing.T) {
	h := testHandler(nil)
	_, err := h.Call(context.Background(), "get_contract", []byte(`{"contract_number":"1"}`))
	if !IsNotFound(err) {
		t.Fatalf("err=%v", err)
	}
}

func TestValidationIsNotEmptySearch(t *testing.T) {
	h := testHandler(nil)
	_, err := h.Call(context.Background(), SearchRecords, []byte(`{"filters":{"contract_number":"12"}}`))
	if !IsValidation(err) {
		t.Fatalf("ждали validation, получили %v", err)
	}
	_, err = h.Call(context.Background(), SearchRecords, []byte(`{"collections":["contracts"]}`))
	if !IsValidation(err) {
		t.Fatalf("коллекция: %v", err)
	}
	_, err = h.Call(context.Background(), SearchRecords, []byte(`{"limit":99}`))
	if !IsValidation(err) {
		t.Fatalf("limit: %v", err)
	}
	_, err = h.Call(context.Background(), BudgetSummary, []byte(`{}`))
	if !IsValidation(err) {
		t.Fatalf("широкий summary: %v", err)
	}
	_, err = h.Call(context.Background(), IngestStatus, []byte(`{"extra":1}`))
	if !IsValidation(err) {
		t.Fatalf("status extra: %v", err)
	}
}

func TestSearchEmptyHits(t *testing.T) {
	h := testHandler(nil)
	out, err := h.Call(context.Background(), SearchRecords, []byte(`{"filters":{"year":1999}}`))
	if err != nil {
		t.Fatal(err)
	}
	res := out.(SearchResult)
	if res.Hits == nil || len(res.Hits) != 0 {
		t.Fatalf("hits=%v", res.Hits)
	}
}

func TestSummaryRemainFreeNull(t *testing.T) {
	lim := 10.0
	h := testHandler([]qdrant.Point{{
		ID: "1",
		Payload: map[string]any{
			"article_code":  "production:1.8.2",
			"article_name":  "электроэнергия",
			"article_level": 3.0,
			"limit_amount":  lim,
			"l2_code":       "production:1.8",
			"l2_name":       "Коммунальные услуги",
			"amount_unit":   "thousand_rub",
			"currency":      "RUB",
		},
	}})
	out, err := h.Call(context.Background(), BudgetSummary, []byte(`{"article_code":"production:1.8"}`))
	if err != nil {
		t.Fatal(err)
	}
	res := out.(SummaryResult)
	if res.Total.Limit == nil || *res.Total.Limit != 10 {
		t.Fatalf("limit %+v", res.Total)
	}
	if res.Total.RemainFree != nil || res.Total.Fact != nil || res.Total.Obligation != nil {
		t.Fatalf("пустые поля должны быть null: %+v", res.Total)
	}
	if len(res.Rows) != 1 || res.NeedRefine {
		t.Fatalf("rows %+v", res)
	}
}

func TestGroupByLevel(t *testing.T) {
	points := []qdrant.Point{
		{Payload: map[string]any{
			"article_code": "production:1.8.1", "article_name": "вода", "article_level": 3.0,
			"l2_code": "production:1.8", "l2_name": "Коммунальные услуги", "limit_amount": 5.0,
		}},
		{Payload: map[string]any{
			"article_code": "production:1.8.2", "article_name": "электроэнергия", "article_level": 3.0,
			"l2_code": "production:1.8", "l2_name": "Коммунальные услуги", "limit_amount": 7.0,
		}},
		{Payload: map[string]any{
			"article_code": "production:2", "article_name": "ФОТ", "article_level": 1.0,
			"limit_amount": 3.0,
		}},
	}
	rows := groupByLevel(points, 2)
	if len(rows) != 2 {
		t.Fatalf("groups %d %+v", len(rows), rows)
	}
	if rows[0].Code != "production:1.8" || rows[0].Limit == nil || *rows[0].Limit != 12 {
		t.Fatalf("первая группа %+v", rows[0])
	}
	if rows[1].Code != "production:2" {
		t.Fatalf("fallback листа %+v", rows[1])
	}
}

func TestSearchFilterOnly(t *testing.T) {
	h := testHandler([]qdrant.Point{{
		ID:      "829dd902-2f8f-5b3e-943d-20c8f354e6cc",
		Payload: map[string]any{"article_code": "production:1.8.2", "source_file": "f.xlsx", "sheet": "Смета затрат", "row": 23.0},
	}})
	out, err := h.Call(context.Background(), SearchRecords, []byte(`{"filters":{"article_code":"production:1.8.2"}}`))
	if err != nil {
		t.Fatal(err)
	}
	res := out.(SearchResult)
	if len(res.Hits) != 1 || res.Hits[0].Score != nil || res.Hits[0].Source.Row == nil || *res.Hits[0].Source.Row != 23 {
		b, _ := json.Marshal(res)
		t.Fatalf("%s", b)
	}
}
