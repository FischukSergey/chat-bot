package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/FischukSergey/chat-bot/mcp_server/internal/config"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/qdrant"
	"github.com/FischukSergey/chat-bot/mcp_server/internal/tools"
)

type fakeStore struct{}

func (fakeStore) Count(context.Context, string, *qdrant.Filter) (int, error) {
	return 0, nil
}
func (fakeStore) Scroll(context.Context, string, qdrant.ScrollRequest) (qdrant.ScrollResult, error) {
	return qdrant.ScrollResult{Points: nil}, nil
}
func (fakeStore) ScrollAll(context.Context, string, *qdrant.Filter, int) ([]qdrant.Point, error) {
	return nil, nil
}
func (fakeStore) Search(context.Context, string, qdrant.SearchRequest) ([]qdrant.Point, error) {
	return nil, nil
}

type fakeEmbed struct{}

func (fakeEmbed) Embed(context.Context, []string) ([][]float64, error) {
	return [][]float64{{0.1}}, nil
}

func TestStdioListAndCall(t *testing.T) {
	h := tools.New(config.Config{
		Collection: "budget_items", LimitMin: 1, LimitMax: 20, LimitDefault: 8,
	}, fakeStore{}, fakeEmbed{})
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_records","arguments":{"filters":{"year":2026}}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_records","arguments":{"filters":{"contract_number":"1"}}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_contract","arguments":{}}}`,
		"",
	}, "\n")
	var out bytes.Buffer
	if err := New(h).Serve(context.Background(), strings.NewReader(in), &out); err != nil {
		t.Fatal(err)
	}
	lines := bytes.Split(bytes.TrimSpace(out.Bytes()), []byte("\n"))
	if len(lines) != 5 {
		t.Fatalf("ответов %d: %s", len(lines), out.String())
	}
	var list struct {
		Result struct {
			Tools []struct {
				Name string `json:"name"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(lines[1], &list); err != nil {
		t.Fatal(err)
	}
	if len(list.Result.Tools) != 3 || list.Result.Tools[0].Name != "search_records" {
		t.Fatalf("list %+v", list.Result.Tools)
	}
	var call struct {
		Result struct {
			IsError bool `json:"isError"`
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(lines[2], &call); err != nil {
		t.Fatal(err)
	}
	if call.Result.IsError || !strings.Contains(call.Result.Content[0].Text, `"hits"`) {
		t.Fatalf("call %s", lines[2])
	}
	if err := json.Unmarshal(lines[3], &call); err != nil {
		t.Fatal(err)
	}
	if !call.Result.IsError || !strings.Contains(call.Result.Content[0].Text, "validation") {
		t.Fatalf("validation %s", lines[3])
	}
	if err := json.Unmarshal(lines[4], &call); err != nil {
		t.Fatal(err)
	}
	if !call.Result.IsError || !strings.Contains(call.Result.Content[0].Text, "get_contract") {
		t.Fatalf("unknown %s", lines[4])
	}
}
