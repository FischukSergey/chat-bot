package tools

import (
	"math"
	"testing"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

func almostEqual(t *testing.T, got, want, eps float64) {
	t.Helper()
	if math.Abs(got-want) > eps {
		t.Fatalf("got %v want %v (eps %v)", got, want, eps)
	}
}

func TestNeedRefineTopN(t *testing.T) {
	h := testHandler([]qdrant.Point{
		{Payload: map[string]any{"article_code": "a", "article_name": "a", "article_level": 1.0, "limit_amount": 3.0}},
		{Payload: map[string]any{"article_code": "b", "article_name": "b", "article_level": 1.0, "limit_amount": 1.0}},
	})
	out, err := h.Call(t.Context(), BudgetSummary, []byte(`{"year":2026,"limit":1}`))
	if err != nil {
		t.Fatal(err)
	}
	res := out.(SummaryResult)
	if !res.NeedRefine || len(res.Rows) != 1 || res.Rows[0].Code != "a" {
		t.Fatalf("%+v", res)
	}
	if res.Total.Limit == nil || *res.Total.Limit != 4 {
		t.Fatalf("total по всем листьям, не по топ-N: %+v", res.Total)
	}
}
