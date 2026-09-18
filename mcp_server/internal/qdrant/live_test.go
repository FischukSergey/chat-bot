package qdrant

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestLiveScrollAndSearch(t *testing.T) {
	if os.Getenv("QDRANT_URL") == "" {
		root := filepath.Join("..", "..", "..", ".env")
		t.Setenv("MCP_ENV_FILE", root)
	}
	base := os.Getenv("QDRANT_URL")
	if base == "" {
		base = "http://127.0.0.1:6333"
	}
	c := New(base)
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()
	if err := c.Ready(ctx); err != nil {
		t.Skip(err)
	}
	year := 2026
	f := BuildFilter(BudgetFilter{ArticleCode: "production:1.8.2", Year: &year})
	sc, err := c.Scroll(ctx, "budget_items", ScrollRequest{Filter: f, Limit: 2})
	if err != nil {
		t.Fatal(err)
	}
	if len(sc.Points) != 1 {
		t.Fatalf("ожидали 1 лист, получили %d", len(sc.Points))
	}
	if sc.Points[0].Payload["article_code"] != "production:1.8.2" {
		t.Fatalf("payload %#v", sc.Points[0].Payload)
	}
	n, err := c.Count(ctx, "budget_items", f)
	if err != nil || n != 1 {
		t.Fatalf("count %d %v", n, err)
	}
	vec := make([]float64, 1024)
	hits, err := c.Search(ctx, "budget_items", SearchRequest{Vector: vec, Filter: f, Limit: 1})
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 1 || hits[0].Payload["article_code"] != "production:1.8.2" {
		t.Fatalf("search %#v", hits)
	}
}
