package embed

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
)

func TestLiveEmbedSize(t *testing.T) {
	if os.Getenv("EMBEDDINGS_MODEL") == "" {
		t.Setenv("MCP_ENV_FILE", filepath.Join("..", "..", "..", ".env"))
	}
	cfg, err := config.Load()
	if err != nil {
		t.Skip(err)
	}
	c := New(cfg)
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	if err := c.Ready(ctx); err != nil {
		t.Skip(err)
	}
	vecs, err := c.Embed(ctx, []string{"электроэнергия производственные"})
	if err != nil {
		t.Fatal(err)
	}
	if len(vecs) != 1 || len(vecs[0]) != cfg.VectorSize {
		t.Fatalf("size %d want %d", len(vecs[0]), cfg.VectorSize)
	}
}
