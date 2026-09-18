// Package mcp — stdio JSON-RPC (MCP): tools/list и tools/call на том же Call.
package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"sync"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/tools"
)

const protocolVersion = "2024-11-05"

// Server читает NDJSON с stdin, пишет ответы в stdout.
type Server struct {
	h   *tools.Handler
	mu  sync.Mutex
	out io.Writer
}

// New — транспорт вокруг общего слоя tools.
func New(h *tools.Handler) *Server {
	return &Server{h: h}
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type callParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

type initParams struct {
	ProtocolVersion string `json:"protocolVersion"`
}

// Serve крутит цикл до EOF или отмены ctx.
func (s *Server) Serve(ctx context.Context, in io.Reader, out io.Writer) error {
	s.out = out
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 0, 64*1024), 1<<20)
	for sc.Scan() {
		if err := ctx.Err(); err != nil {
			return err
		}
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		if err := s.handleLine(ctx, line); err != nil {
			return err
		}
	}
	return sc.Err()
}

func (s *Server) handleLine(ctx context.Context, line []byte) error {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		return s.write(map[string]any{
			"jsonrpc": "2.0",
			"id":      nil,
			"error":   rpcError{Code: -32700, Message: "parse error"},
		})
	}
	notify := len(req.ID) == 0 || string(req.ID) == "null"
	switch req.Method {
	case "notifications/initialized", "notifications/cancelled":
		return nil
	case "initialize":
		ver := protocolVersion
		var p initParams
		_ = json.Unmarshal(req.Params, &p)
		if p.ProtocolVersion != "" {
			ver = p.ProtocolVersion
		}
		return s.reply(req.ID, map[string]any{
			"protocolVersion": ver,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "chat-bot", "version": "0.3.0"},
		})
	case "ping":
		return s.reply(req.ID, map[string]any{})
	case "tools/list":
		list := make([]map[string]any, 0, 3)
		for _, spec := range tools.Specs() {
			list = append(list, map[string]any{
				"name":        spec.Name,
				"description": spec.Description,
				"inputSchema": spec.InputSchema,
			})
		}
		return s.reply(req.ID, map[string]any{"tools": list})
	case "tools/call":
		var p callParams
		if err := json.Unmarshal(req.Params, &p); err != nil || p.Name == "" {
			return s.replyError(req.ID, -32602, "invalid params")
		}
		out, err := s.h.Call(ctx, p.Name, p.Arguments)
		if err != nil {
			text := err.Error()
			return s.reply(req.ID, map[string]any{
				"content": []map[string]any{{"type": "text", "text": text}},
				"isError": true,
			})
		}
		raw, err := json.Marshal(out)
		if err != nil {
			return s.replyError(req.ID, -32603, err.Error())
		}
		return s.reply(req.ID, map[string]any{
			"content": []map[string]any{{"type": "text", "text": string(raw)}},
		})
	case "resources/list":
		return s.reply(req.ID, map[string]any{"resources": []any{}})
	case "prompts/list":
		return s.reply(req.ID, map[string]any{"prompts": []any{}})
	default:
		if notify {
			return nil
		}
		return s.replyError(req.ID, -32601, fmt.Sprintf("method %q not found", req.Method))
	}
}

func (s *Server) reply(id json.RawMessage, result any) error {
	if len(id) == 0 || string(id) == "null" {
		return nil
	}
	return s.write(map[string]any{"jsonrpc": "2.0", "id": json.RawMessage(id), "result": result})
}

func (s *Server) replyError(id json.RawMessage, code int, msg string) error {
	if len(id) == 0 || string(id) == "null" {
		return nil
	}
	return s.write(map[string]any{"jsonrpc": "2.0", "id": json.RawMessage(id), "error": rpcError{Code: code, Message: msg}})
}

func (s *Server) write(v any) error {
	raw, err := json.Marshal(v)
	if err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	_, err = s.out.Write(append(raw, '\n'))
	return err
}
