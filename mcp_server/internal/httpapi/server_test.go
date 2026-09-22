package httpapi

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/embed"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

func TestHealthOK(t *testing.T) {
	qdMux := http.NewServeMux()
	qdMux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte("ok"))
	})
	qdMux.HandleFunc("POST /collections/budget_items/points/count", func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"result": map[string]any{"count": 172}})
	})
	qd := httptest.NewServer(qdMux)
	t.Cleanup(qd.Close)
	embSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/models" {
			t.Fatalf("path %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"data":[]}`))
	}))
	t.Cleanup(embSrv.Close)
	cfg := config.Config{
		QdrantURL:       qd.URL,
		Collection:      "budget_items",
		EmbeddingsURL:   embSrv.URL,
		EmbeddingsModel: "m",
		VectorSize:      1024,
		HTTPAddr:        "127.0.0.1:0",
	}
	s := New(cfg, qdrant.New(cfg.QdrantURL), embed.New(cfg))
	rec := httptest.NewRecorder()
	s.Handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/health", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("code %d body %s", rec.Code, rec.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "ok" || body["qdrant"] != "ok" || body["embeddings"] != "ok" {
		t.Fatalf("%v", body)
	}
	if body["points"] != float64(172) {
		t.Fatalf("points %v", body["points"])
	}
}

func TestHealthMissingCollectionOK(t *testing.T) {
	qdMux := http.NewServeMux()
	qdMux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte("ok"))
	})
	qdMux.HandleFunc("POST /collections/budget_items/points/count", func(w http.ResponseWriter, _ *http.Request) {
		http.Error(w, `{"status":{"error":"Not found"}}`, http.StatusNotFound)
	})
	qd := httptest.NewServer(qdMux)
	t.Cleanup(qd.Close)
	embSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"data":[]}`))
	}))
	t.Cleanup(embSrv.Close)
	cfg := config.Config{
		QdrantURL: qd.URL, Collection: "budget_items",
		EmbeddingsURL: embSrv.URL, EmbeddingsModel: "m", VectorSize: 1024,
	}
	s := New(cfg, qdrant.New(cfg.QdrantURL), embed.New(cfg))
	rec := httptest.NewRecorder()
	s.Handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/health", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("code %d body %s", rec.Code, rec.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["points"] != float64(0) {
		t.Fatalf("points %v", body["points"])
	}
}

func TestToolValidationNotEmptyHits(t *testing.T) {
	qdMux := http.NewServeMux()
	qdMux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte("ok"))
	})
	qdMux.HandleFunc("POST /collections/budget_items/points/count", func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"result": map[string]any{"count": 0}})
	})
	qd := httptest.NewServer(qdMux)
	t.Cleanup(qd.Close)
	embSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"data":[]}`))
	}))
	t.Cleanup(embSrv.Close)
	cfg := config.Config{
		QdrantURL: qd.URL, Collection: "budget_items",
		EmbeddingsURL: embSrv.URL, EmbeddingsModel: "m", VectorSize: 2,
		LimitMin: 1, LimitMax: 20, LimitDefault: 8,
	}
	s := New(cfg, qdrant.New(cfg.QdrantURL), embed.New(cfg))
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/tools/search_records", strings.NewReader(`{"collections":["contracts"]}`))
	s.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("code %d body %s", rec.Code, rec.Body.String())
	}
	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodPost, "/tools/get_contract", strings.NewReader(`{}`))
	s.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get_contract %d %s", rec.Code, rec.Body.String())
	}
}
