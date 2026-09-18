package qdrant

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCountScrollSearch(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte("all shards are ready"))
	})
	mux.HandleFunc("POST /collections/budget_items/points/count", func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"result": map[string]any{"count": 172}})
	})
	mux.HandleFunc("POST /collections/budget_items/points/scroll", func(w http.ResponseWriter, r *http.Request) {
		var req map[string]any
		_ = json.NewDecoder(r.Body).Decode(&req)
		if req["with_vector"] != false {
			t.Fatalf("with_vector=%v", req["with_vector"])
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"result": map[string]any{
				"points": []map[string]any{
					{"id": "829dd902-2f8f-5b3e-943d-20c8f354e6cc", "payload": map[string]any{"article_code": "production:1.8.2"}},
				},
			},
		})
	})
	mux.HandleFunc("POST /collections/budget_items/points/search", func(w http.ResponseWriter, r *http.Request) {
		var req map[string]any
		_ = json.NewDecoder(r.Body).Decode(&req)
		if _, ok := req["vector"]; !ok {
			t.Fatal("нет vector")
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"result": []map[string]any{
				{"id": 1, "score": 0.9, "payload": map[string]any{"article_code": "production:1.8.2"}},
			},
		})
	})
	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	c := New(srv.URL)
	ctx := context.Background()
	if err := c.Ready(ctx); err != nil {
		t.Fatal(err)
	}
	n, err := c.Count(ctx, "budget_items", nil)
	if err != nil || n != 172 {
		t.Fatalf("count %d %v", n, err)
	}
	year := 2026
	sc, err := c.Scroll(ctx, "budget_items", ScrollRequest{Filter: BuildFilter(BudgetFilter{Year: &year}), Limit: 1})
	if err != nil || len(sc.Points) != 1 || sc.Points[0].ID != "829dd902-2f8f-5b3e-943d-20c8f354e6cc" {
		t.Fatalf("scroll %#v %v", sc, err)
	}
	hits, err := c.Search(ctx, "budget_items", SearchRequest{Vector: []float64{0.1, 0.2}, Limit: 1, ScoreThreshold: 0.4})
	if err != nil || len(hits) != 1 || hits[0].ID != "1" || hits[0].Score < 0.8 {
		t.Fatalf("search %#v %v", hits, err)
	}
}
