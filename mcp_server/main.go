package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"slices"
	"syscall"
	"time"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/embed"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/httpapi"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/mcp"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/tools"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelInfo})))
	cfg, err := config.Load()
	if err != nil {
		return err
	}
	qd := qdrant.New(cfg.QdrantURL)
	emb := embed.New(cfg)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if useStdio() {
		fmt.Fprintln(os.Stderr, "mcp_server stdio  tools/list tools/call")
		return mcp.New(tools.New(cfg, qd, emb)).Serve(ctx, os.Stdin, os.Stdout)
	}

	srv := httpapi.New(cfg, qd, emb)
	errCh := make(chan error, 1)
	go func() {
		fmt.Fprintf(os.Stderr, "mcp_server HTTP %s  GET /health  POST /tools/{name}\n", cfg.HTTPAddr)
		errCh <- srv.ListenAndServe()
	}()
	select {
	case err := <-errCh:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	case <-ctx.Done():
		shut, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return srv.Shutdown(shut)
	}
}

func useStdio() bool {
	if slices.Contains(os.Args[1:], "--stdio") {
		return true
	}
	return os.Getenv("MCP_TRANSPORT") == "stdio"
}
