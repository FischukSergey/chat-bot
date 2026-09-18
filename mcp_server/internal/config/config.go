// Package config читает .env так же, как ingest: не перезаписывает уже заданные переменные.
package config

import (
	"cmp"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Config — то, что нужно каркасу MCP: Qdrant, embeddings, HTTP, лимиты поиска.
type Config struct {
	QdrantURL       string
	Collection      string
	EmbeddingsURL   string
	EmbeddingsModel string
	VectorSize      int
	HTTPAddr        string
	LimitMin        int
	LimitMax        int
	LimitDefault    int
	ScoreThreshold  float64
}

// Load читает окружение и первый найденный .env (cwd, родитель, MCP_ENV_FILE).
func Load() (Config, error) {
	loadDotEnv()
	size, err := strconv.Atoi(strings.TrimSpace(os.Getenv("VECTOR_SIZE")))
	if err != nil || size <= 0 {
		return Config{}, fmt.Errorf("VECTOR_SIZE должен быть > 0 (длина /v1/embeddings)")
	}
	model := strings.TrimSpace(os.Getenv("EMBEDDINGS_MODEL"))
	if model == "" {
		return Config{}, fmt.Errorf("EMBEDDINGS_MODEL пуст")
	}
	threshold := 0.4
	if raw := strings.TrimSpace(os.Getenv("SEARCH_SCORE_THRESHOLD")); raw != "" {
		v, perr := strconv.ParseFloat(raw, 64)
		if perr != nil {
			return Config{}, fmt.Errorf("SEARCH_SCORE_THRESHOLD: %w", perr)
		}
		threshold = v
	}
	return Config{
		QdrantURL:       cmp.Or(strings.TrimSpace(os.Getenv("QDRANT_URL")), "http://127.0.0.1:6333"),
		Collection:      cmp.Or(strings.TrimSpace(os.Getenv("QDRANT_COLLECTION_BUDGET")), "budget_items"),
		EmbeddingsURL:   strings.TrimRight(cmp.Or(strings.TrimSpace(os.Getenv("EMBEDDINGS_URL")), "http://127.0.0.1:1234/v1"), "/"),
		EmbeddingsModel: model,
		VectorSize:      size,
		HTTPAddr:        cmp.Or(strings.TrimSpace(os.Getenv("MCP_HTTP_ADDR")), "127.0.0.1:7345"),
		LimitMin:        1,
		LimitMax:        20,
		LimitDefault:    8,
		ScoreThreshold:  threshold,
	}, nil
}

func loadDotEnv() {
	seen := false
	if p := strings.TrimSpace(os.Getenv("MCP_ENV_FILE")); p != "" {
		if applyEnvFile(p) {
			seen = true
		}
	}
	if seen {
		return
	}
	cwd, err := os.Getwd()
	if err != nil {
		return
	}
	for _, p := range []string{filepath.Join(cwd, ".env"), filepath.Join(cwd, "..", ".env")} {
		if applyEnvFile(p) {
			return
		}
	}
}

func applyEnvFile(path string) bool {
	data, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	for line := range strings.SplitSeq(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
			continue
		}
		key, val, _ := strings.Cut(line, "=")
		key = strings.TrimSpace(key)
		val = strings.TrimSpace(val)
		if key == "" {
			continue
		}
		if _, ok := os.LookupEnv(key); ok {
			continue
		}
		_ = os.Setenv(key, val)
	}
	return true
}
