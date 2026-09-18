// Package mcp — stdio-транспорт. Подключение tools/list и tools/call — пункт 4.
package mcp

// Stdio ещё не слушает: HTTP /health уже есть, MCP-протокол — следующий пункт.
type Stdio struct{}
