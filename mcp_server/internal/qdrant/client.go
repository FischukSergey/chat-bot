package qdrant

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// Client — REST к Qdrant 1.15: ready, count, scroll, search.
type Client struct {
	base string
	http *http.Client
}

// New ходит на QDRANT_URL без завершающего слэша.
func New(baseURL string) *Client {
	return &Client{
		base: strings.TrimRight(baseURL, "/"),
		http: &http.Client{Timeout: 30 * time.Second},
	}
}

// Ready проверяет GET /readyz.
func (c *Client) Ready(ctx context.Context) error {
	code, body, err := c.do(ctx, http.MethodGet, "/readyz", nil)
	if err != nil {
		return err
	}
	if code >= 400 {
		return fmt.Errorf("qdrant readyz HTTP %d: %s", code, trim(body))
	}
	return nil
}

// Count — точный count коллекции, опционально с filter.
func (c *Client) Count(ctx context.Context, collection string, filter *Filter) (int, error) {
	payload := map[string]any{"exact": true}
	if filter != nil {
		payload["filter"] = filter
	}
	var out struct {
		Result struct {
			Count int `json:"count"`
		} `json:"result"`
	}
	if err := c.postJSON(ctx, "/collections/"+collection+"/points/count", payload, &out); err != nil {
		return 0, err
	}
	return out.Result.Count, nil
}

// ScrollRequest — выборка без вектора.
type ScrollRequest struct {
	Filter *Filter `json:"filter,omitempty"`
	Limit  int     `json:"limit,omitempty"`
	Offset any     `json:"offset,omitempty"`
}

// ScrollResult — точки и курсор следующей страницы.
type ScrollResult struct {
	Points []Point `json:"points"`
	Next   any     `json:"next_page_offset"`
}

// Point — id + payload; Score только у search.
type Point struct {
	ID      PointID        `json:"id"`
	Score   float64        `json:"score,omitempty"`
	Payload map[string]any `json:"payload"`
}

// PointID — UUID-строка или числовой id Qdrant.
type PointID string

// UnmarshalJSON принимает JSON-строку или число.
func (id *PointID) UnmarshalJSON(b []byte) error {
	b = bytes.TrimSpace(b)
	if len(b) == 0 || string(b) == "null" {
		*id = ""
		return nil
	}
	if b[0] == '"' {
		var s string
		if err := json.Unmarshal(b, &s); err != nil {
			return err
		}
		*id = PointID(s)
		return nil
	}
	*id = PointID(string(b))
	return nil
}

// Scroll — POST /points/scroll, без векторов.
func (c *Client) Scroll(ctx context.Context, collection string, req ScrollRequest) (ScrollResult, error) {
	if req.Limit <= 0 {
		req.Limit = 8
	}
	body := map[string]any{
		"limit":        req.Limit,
		"with_payload": true,
		"with_vector":  false,
	}
	if req.Filter != nil {
		body["filter"] = req.Filter
	}
	if req.Offset != nil {
		body["offset"] = req.Offset
	}
	var out struct {
		Result ScrollResult `json:"result"`
	}
	if err := c.postJSON(ctx, "/collections/"+collection+"/points/scroll", body, &out); err != nil {
		return ScrollResult{}, err
	}
	return out.Result, nil
}

// ScrollAll листает scroll до конца.
func (c *Client) ScrollAll(ctx context.Context, collection string, filter *Filter, pageSize int) ([]Point, error) {
	if pageSize <= 0 {
		pageSize = 128
	}
	var all []Point
	var offset any
	for {
		res, err := c.Scroll(ctx, collection, ScrollRequest{Filter: filter, Limit: pageSize, Offset: offset})
		if err != nil {
			return nil, err
		}
		all = append(all, res.Points...)
		if res.Next == nil || len(res.Points) == 0 {
			break
		}
		offset = res.Next
	}
	return all, nil
}

// SearchRequest — вектор + тот же filter.
type SearchRequest struct {
	Vector         []float64
	Filter         *Filter
	Limit          int
	ScoreThreshold float64
}

// Search — POST /points/search.
func (c *Client) Search(ctx context.Context, collection string, req SearchRequest) ([]Point, error) {
	if req.Limit <= 0 {
		req.Limit = 8
	}
	body := map[string]any{
		"vector":       req.Vector,
		"limit":        req.Limit,
		"with_payload": true,
		"with_vector":  false,
	}
	if req.Filter != nil {
		body["filter"] = req.Filter
	}
	if req.ScoreThreshold > 0 {
		body["score_threshold"] = req.ScoreThreshold
	}
	var out struct {
		Result []Point `json:"result"`
	}
	if err := c.postJSON(ctx, "/collections/"+collection+"/points/search", body, &out); err != nil {
		return nil, err
	}
	return out.Result, nil
}

func (c *Client) postJSON(ctx context.Context, path string, payload any, dest any) error {
	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	code, body, err := c.do(ctx, http.MethodPost, path, raw)
	if err != nil {
		return err
	}
	if code >= 400 {
		return fmt.Errorf("qdrant %s HTTP %d: %s", path, code, trim(body))
	}
	if dest == nil {
		return nil
	}
	if err := json.Unmarshal(body, dest); err != nil {
		return fmt.Errorf("qdrant %s: %w", path, err)
	}
	return nil
}

func (c *Client) do(ctx context.Context, method, path string, payload []byte) (int, []byte, error) {
	var rdr io.Reader
	if payload != nil {
		rdr = bytes.NewReader(payload)
	}
	req, err := http.NewRequestWithContext(ctx, method, c.base+path, rdr)
	if err != nil {
		return 0, nil, err
	}
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return 0, nil, fmt.Errorf("qdrant: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, nil, err
	}
	return resp.StatusCode, body, nil
}

func trim(b []byte) string {
	s := strings.TrimSpace(string(b))
	if len(s) > 300 {
		return s[:300]
	}
	return s
}
