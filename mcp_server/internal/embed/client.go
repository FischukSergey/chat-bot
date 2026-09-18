package embed

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
)

// Client — OpenAI-compatible /v1/embeddings, та же модель и размер, что ingest.
type Client struct {
	base  string
	model string
	size  int
	http  *http.Client
}

// New из конфига ingest/MCP (EMBEDDINGS_URL, EMBEDDINGS_MODEL, VECTOR_SIZE).
func New(cfg config.Config) *Client {
	return &Client{
		base:  cfg.EmbeddingsURL,
		model: cfg.EmbeddingsModel,
		size:  cfg.VectorSize,
		http:  &http.Client{Timeout: 120 * time.Second},
	}
}

// Model — имя из .env, не «что сейчас в UI Studio».
func (c *Client) Model() string { return c.model }

// VectorSize — ожидаемая длина вектора.
func (c *Client) VectorSize() int { return c.size }

// Ready — GET /models, без инференса.
func (c *Client) Ready(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.base+"/models", nil)
	if err != nil {
		return err
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("embeddings: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 512))
	if err != nil {
		return err
	}
	if resp.StatusCode >= 400 {
		return fmt.Errorf("embeddings models HTTP %d: %s", resp.StatusCode, bytes.TrimSpace(body))
	}
	return nil
}

// Embed возвращает векторы в том же порядке, что texts. Пустой вход — пустой выход.
func (c *Client) Embed(ctx context.Context, texts []string) ([][]float64, error) {
	if len(texts) == 0 {
		return nil, nil
	}
	payload, err := json.Marshal(map[string]any{
		"model": c.model,
		"input": texts,
	})
	if err != nil {
		return nil, err
	}
	var last error
	for attempt := range 3 {
		vecs, err := c.embedOnce(ctx, payload, len(texts))
		if err == nil {
			return vecs, nil
		}
		last = err
		if !isTransient(err) || ctx.Err() != nil {
			return nil, err
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Duration(500*(1<<attempt)) * time.Millisecond):
		}
	}
	return nil, fmt.Errorf("embeddings недоступны после 3 попыток: %w", last)
}

type transientError struct{ error }

func isTransient(err error) bool {
	var t *transientError
	return errors.As(err, &t)
}

func (c *Client) embedOnce(ctx context.Context, payload []byte, n int) ([][]float64, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.base+"/embeddings", bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, &transientError{fmt.Errorf("embeddings: %w", err)}
	}
	defer func() { _ = resp.Body.Close() }()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, &transientError{err}
	}
	if resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500 {
		return nil, &transientError{fmt.Errorf("embeddings HTTP %d: %s", resp.StatusCode, trim(body))}
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("embeddings HTTP %d: %s", resp.StatusCode, trim(body))
	}
	var out struct {
		Data []struct {
			Index     int       `json:"index"`
			Embedding []float64 `json:"embedding"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, fmt.Errorf("embeddings: %w", err)
	}
	if len(out.Data) != n {
		return nil, fmt.Errorf("ожидали %d векторов, пришло %d", n, len(out.Data))
	}
	vecs := make([][]float64, n)
	for _, row := range out.Data {
		if row.Index < 0 || row.Index >= n {
			return nil, fmt.Errorf("embeddings: плохой index %d", row.Index)
		}
		if len(row.Embedding) != c.size {
			return nil, fmt.Errorf("длина вектора %d ≠ VECTOR_SIZE %d", len(row.Embedding), c.size)
		}
		if vecs[row.Index] != nil {
			return nil, fmt.Errorf("embeddings: повторный index %d", row.Index)
		}
		vecs[row.Index] = row.Embedding
	}
	for i, v := range vecs {
		if v == nil {
			return nil, fmt.Errorf("embeddings: нет вектора index %d", i)
		}
	}
	return vecs, nil
}

func trim(b []byte) string {
	s := string(bytes.TrimSpace(b))
	if len(s) > 300 {
		return s[:300]
	}
	return s
}
