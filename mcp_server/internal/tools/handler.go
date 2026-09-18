package tools

import (
	"context"
	"encoding/json"
	"log/slog"
	"time"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
)

// Store — Qdrant для tools.
type Store interface {
	Count(ctx context.Context, collection string, filter *qdrant.Filter) (int, error)
	Scroll(ctx context.Context, collection string, req qdrant.ScrollRequest) (qdrant.ScrollResult, error)
	ScrollAll(ctx context.Context, collection string, filter *qdrant.Filter, pageSize int) ([]qdrant.Point, error)
	Search(ctx context.Context, collection string, req qdrant.SearchRequest) ([]qdrant.Point, error)
}

// Embedder — та же модель, что ingest.
type Embedder interface {
	Embed(ctx context.Context, texts []string) ([][]float64, error)
}

// Handler — единственный слой tools (HTTP и MCP зовут Call).
type Handler struct {
	cfg config.Config
	qd  Store
	emb Embedder
}

// New собирает обработчики search_records / budget_summary / ingest_status.
func New(cfg config.Config, qd Store, emb Embedder) *Handler {
	return &Handler{cfg: cfg, qd: qd, emb: emb}
}

// Call выполняет tool по имени. Неизвестный tool — not_found, не пустой ответ.
// Лог на stderr: tool, latency_ms, hits, error — и HTTP, и stdio.
func (h *Handler) Call(ctx context.Context, name string, raw json.RawMessage) (any, error) {
	start := time.Now()
	out, err := h.dispatch(ctx, name, raw)
	slog.Info("tool",
		"tool", name,
		"latency_ms", time.Since(start).Milliseconds(),
		"hits", hitCount(out),
		"error", errKind(err),
	)
	return out, err
}

func (h *Handler) dispatch(ctx context.Context, name string, raw json.RawMessage) (any, error) {
	switch name {
	case SearchRecords:
		return h.searchRecords(ctx, raw)
	case BudgetSummary:
		return h.budgetSummary(ctx, raw)
	case IngestStatus:
		return h.ingestStatus(ctx, raw)
	default:
		return nil, notFoundError("tool %q не реализован", name)
	}
}

func hitCount(out any) int {
	switch v := out.(type) {
	case SearchResult:
		return len(v.Hits)
	case SummaryResult:
		return len(v.Rows)
	case StatusResult:
		if len(v.Collections) == 0 {
			return 0
		}
		return v.Collections[0].Points
	default:
		return 0
	}
}

func errKind(err error) string {
	switch {
	case err == nil:
		return ""
	case IsValidation(err):
		return "validation"
	case IsNotFound(err):
		return "not_found"
	default:
		return "error"
	}
}
