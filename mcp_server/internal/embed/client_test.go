package embed

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
)

func TestEmbedOrderAndSize(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/embeddings" {
			t.Fatalf("path %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"data": []map[string]any{
				{"index": 1, "embedding": []float64{0, 1}},
				{"index": 0, "embedding": []float64{2, 3}},
			},
		})
	}))
	t.Cleanup(srv.Close)
	c := New(config.Config{EmbeddingsURL: srv.URL, EmbeddingsModel: "m", VectorSize: 2})
	vecs, err := c.Embed(context.Background(), []string{"a", "b"})
	if err != nil {
		t.Fatal(err)
	}
	if vecs[0][0] != 2 || vecs[1][0] != 0 {
		t.Fatalf("порядок: %#v", vecs)
	}
}

func TestEmbedRejectsWrongSize(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"data": []map[string]any{{"index": 0, "embedding": []float64{1}}},
		})
	}))
	t.Cleanup(srv.Close)
	c := New(config.Config{EmbeddingsURL: srv.URL, EmbeddingsModel: "m", VectorSize: 2})
	_, err := c.Embed(context.Background(), []string{"a"})
	if err == nil {
		t.Fatal("ждали ошибку размера")
	}
}
