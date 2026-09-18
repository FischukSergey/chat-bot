package tools

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/embed"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

func liveHandler(t *testing.T) *Handler {
	t.Helper()
	if os.Getenv("EMBEDDINGS_MODEL") == "" {
		t.Setenv("MCP_ENV_FILE", filepath.Join("..", "..", "..", ".env"))
	}
	cfg, err := config.Load()
	if err != nil {
		t.Skip(err)
	}
	qd := qdrant.New(cfg.QdrantURL)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := qd.Ready(ctx); err != nil {
		t.Skip(err)
	}
	return New(cfg, qd, embed.New(cfg))
}

func TestLiveSearchAndSummary(t *testing.T) {
	h := liveHandler(t)
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	out, err := h.Call(ctx, SearchRecords, json.RawMessage(`{"filters":{"article_code":"production:1.8.2"}}`))
	if err != nil {
		t.Fatal(err)
	}
	hits := out.(SearchResult).Hits
	if len(hits) != 1 || hits[0].Fields["article_code"] != "production:1.8.2" {
		t.Fatalf("search %+v", hits)
	}
	lim, ok := hits[0].Fields["limit_amount"].(float64)
	if !ok {
		t.Fatalf("limit type %T", hits[0].Fields["limit_amount"])
	}
	almostEqual(t, lim, 124970.29767396959, 1e-6)
	if hits[0].Fields["fact_amount"] != nil || hits[0].Fields["remain_free"] != nil {
		t.Fatalf("факт/остаток не null: %+v", hits[0].Fields)
	}

	empty, err := h.Call(ctx, SearchRecords, json.RawMessage(`{"filters":{"article_code":"production:9.9.9"}}`))
	if err != nil {
		t.Fatal(err)
	}
	if n := len(empty.(SearchResult).Hits); n != 0 {
		t.Fatalf("несуществующий код: %d хитов", n)
	}

	sum, err := h.Call(ctx, BudgetSummary, json.RawMessage(`{"article_code":"production:1.8","expense_kind":"production"}`))
	if err != nil {
		t.Fatal(err)
	}
	res := sum.(SummaryResult)
	if res.Total.RemainFree != nil || res.Total.Fact != nil || res.Total.Obligation != nil {
		t.Fatalf("как в Excel — null: %+v", res.Total)
	}
	if res.Total.Limit == nil {
		t.Fatal("лимит ветки 1.8 пуст")
	}
	almostEqual(t, *res.Total.Limit, 136220.7035623236, 1e-6)
	if len(res.Rows) != 3 {
		t.Fatalf("листья 1.8: %d", len(res.Rows))
	}

	year, err := h.Call(ctx, BudgetSummary, json.RawMessage(`{"year":2026,"expense_kind":"production","limit":50}`))
	if err != nil {
		t.Fatal(err)
	}
	prod := year.(SummaryResult)
	if prod.Total.Limit == nil {
		t.Fatal("лимит production пуст")
	}
	almostEqual(t, *prod.Total.Limit, 9566769.39204496, 0.01)
	if !prod.NeedRefine {
		t.Fatal("99 листьев при limit 50 — need_refine")
	}

	st, err := h.Call(ctx, IngestStatus, json.RawMessage(`{}`))
	if err != nil {
		t.Fatal(err)
	}
	cols := st.(StatusResult).Collections
	if len(cols) != 1 || cols[0].Name != "budget_items" || cols[0].Points != 172 {
		t.Fatalf("status %+v", cols)
	}
}
