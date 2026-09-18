// Package tools — слой обработчиков MCP. Реализация — пункт 3 чек-листа.
package tools

const (
	SearchRecords = "search_records"
	BudgetSummary = "budget_summary"
	IngestStatus  = "ingest_status"
)

// Names — tools Sprint 3. get_contract / list_obligations не регистрируем.
func Names() []string {
	return []string{SearchRecords, BudgetSummary, IngestStatus}
}
