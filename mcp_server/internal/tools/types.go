package tools

// Source — Excel-строка, как в payload ingest.
type Source struct {
	SourceFile string `json:"source_file"`
	Sheet      string `json:"sheet"`
	Row        *int   `json:"row"`
}

// MoneyFields — суммы как в индексе. null ≠ 0.
type MoneyFields struct {
	Limit            *float64 `json:"limit"`
	Fact             *float64 `json:"fact"`
	Obligation       *float64 `json:"obligation"`
	RemainFree       *float64 `json:"remain_free"`
	RemainUnexecuted *float64 `json:"remain_unexecuted"`
	AmountUnit       string   `json:"amount_unit"`
	Currency         string   `json:"currency"`
}

// Hit — элемент search_records.
type Hit struct {
	Collection string         `json:"collection"`
	ID         string         `json:"id"`
	Score      *float64       `json:"score"`
	Fields     map[string]any `json:"fields"`
	Source     Source         `json:"source"`
}

// SearchResult — выход search_records.
type SearchResult struct {
	Hits []Hit `json:"hits"`
}

// SummaryRow — лист или группа group_by_level.
type SummaryRow struct {
	Code  string `json:"code"`
	Name  string `json:"name"`
	Level int    `json:"level"`
	MoneyFields
}

// SummaryResult — выход budget_summary.
type SummaryResult struct {
	Filter     map[string]any `json:"filter"`
	Total      MoneyFields    `json:"total"`
	Rows       []SummaryRow   `json:"rows"`
	NeedRefine bool           `json:"need_refine"`
}

// StatusResult — выход ingest_status.
type StatusResult struct {
	Collections []CollectionStatus `json:"collections"`
}

// CollectionStatus — одна коллекция индекса.
type CollectionStatus struct {
	Name          string   `json:"name"`
	Points        int      `json:"points"`
	SourceFiles   []string `json:"source_files"`
	LastIndexedAt *string  `json:"last_indexed_at"`
}
