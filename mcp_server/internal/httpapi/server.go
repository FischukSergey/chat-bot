package httpapi

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/embed"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/tools"
)

// Server — HTTP: /health и POST /tools/{name} → tools.Call.
type Server struct {
	cfg   config.Config
	qd    *qdrant.Client
	emb   *embed.Client
	tools *tools.Handler
	http.Server
}

// New поднимает mux.
func New(cfg config.Config, qd *qdrant.Client, emb *embed.Client) *Server {
	s := &Server{cfg: cfg, qd: qd, emb: emb, tools: tools.New(cfg, qd, emb)}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /tools/{name}", s.handleTool)
	s.Server = http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
	return s
}

type healthBody struct {
	Status          string   `json:"status"`
	Qdrant          string   `json:"qdrant"`
	Embeddings      string   `json:"embeddings"`
	Collection      string   `json:"collection"`
	Points          *int     `json:"points,omitempty"`
	EmbeddingsModel string   `json:"embeddings_model"`
	VectorSize      int      `json:"vector_size"`
	Tools           []string `json:"tools"`
	Error           string   `json:"error,omitempty"`
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	body := healthBody{
		Status:          "ok",
		Qdrant:          "ok",
		Embeddings:      "ok",
		Collection:      s.cfg.Collection,
		EmbeddingsModel: s.cfg.EmbeddingsModel,
		VectorSize:      s.cfg.VectorSize,
		Tools:           tools.Names(),
	}
	code := http.StatusOK
	if err := s.qd.Ready(ctx); err != nil {
		body.Status = "error"
		body.Qdrant = "error"
		body.Error = err.Error()
		code = http.StatusServiceUnavailable
	} else {
		n, err := s.qd.Count(ctx, s.cfg.Collection, nil)
		if err != nil && !isMissingCollection(err) {
			body.Status = "error"
			body.Qdrant = "error"
			body.Error = err.Error()
			code = http.StatusServiceUnavailable
		} else {
			if err != nil {
				n = 0
			}
			body.Points = &n
		}
	}
	if err := s.emb.Ready(ctx); err != nil {
		body.Status = "error"
		body.Embeddings = "error"
		if body.Error == "" {
			body.Error = err.Error()
		}
		code = http.StatusServiceUnavailable
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(body)
}

func (s *Server) handleTool(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	raw, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		writeToolError(w, http.StatusBadRequest, "validation", err.Error())
		return
	}
	name := r.PathValue("name")
	out, err := s.tools.Call(ctx, name, raw)
	if err != nil {
		switch {
		case tools.IsValidation(err):
			writeToolError(w, http.StatusBadRequest, "validation", err.Error())
		case tools.IsNotFound(err):
			writeToolError(w, http.StatusNotFound, "not_found", err.Error())
		default:
			writeToolError(w, http.StatusInternalServerError, "error", err.Error())
		}
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(out)
}

func isMissingCollection(err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	return strings.Contains(msg, "HTTP 404") || strings.Contains(strings.ToLower(msg), "not found")
}

func writeToolError(w http.ResponseWriter, code int, kind, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": kind, "message": msg})
}
