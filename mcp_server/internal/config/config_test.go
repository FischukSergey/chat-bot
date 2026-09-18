package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadRequiresVectorAndModel(t *testing.T) {
	t.Setenv("VECTOR_SIZE", "")
	t.Setenv("EMBEDDINGS_MODEL", "")
	t.Setenv("MCP_ENV_FILE", "/no/such/.env")
	if _, err := Load(); err == nil {
		t.Fatal("ждали ошибку VECTOR_SIZE")
	}
	t.Setenv("VECTOR_SIZE", "1024")
	if _, err := Load(); err == nil {
		t.Fatal("ждали ошибку EMBEDDINGS_MODEL")
	}
	t.Setenv("EMBEDDINGS_MODEL", "text-embedding-qwen3-embedding-0.6b")
	t.Setenv("QDRANT_URL", "http://127.0.0.1:6333")
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Collection != "budget_items" || cfg.VectorSize != 1024 || cfg.LimitDefault != 8 {
		t.Fatalf("%+v", cfg)
	}
}

func TestApplyEnvFileDoesNotOverride(t *testing.T) {
	t.Setenv("ALREADY", "keep")
	dir := t.TempDir()
	path := filepath.Join(dir, ".env")
	if err := os.WriteFile(path, []byte("ALREADY=new\nMCP_TEST_FOO=bar\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Unsetenv("MCP_TEST_FOO") })
	if !applyEnvFile(path) {
		t.Fatal("file")
	}
	if got := os.Getenv("ALREADY"); got != "keep" {
		t.Fatalf("overrode ALREADY=%s", got)
	}
	if got := os.Getenv("MCP_TEST_FOO"); got != "bar" {
		t.Fatalf("MCP_TEST_FOO=%s", got)
	}
}
