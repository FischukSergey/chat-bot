package tools

// Spec — описание tool для MCP tools/list.
type Spec struct {
	Name        string
	Description string
	InputSchema map[string]any
}

// Specs — контракт Sprint 3. get_contract / list_obligations не отдаём.
func Specs() []Spec {
	filters := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"properties": map[string]any{
			"year":          map[string]any{"type": "integer"},
			"expense_kind":  map[string]any{"type": "string", "enum": []string{"production", "management"}},
			"article_code":  map[string]any{"type": "string"},
			"article_name":  map[string]any{"type": "string"},
			"match_key":     map[string]any{"type": "string"},
			"ancestor_code": map[string]any{"type": "string"},
			"amount_min":    map[string]any{"type": "number"},
			"amount_max":    map[string]any{"type": "number"},
		},
	}
	return []Spec{
		{
			Name:        SearchRecords,
			Description: "Гибридный поиск по смете: текст и/или фильтры. Только budget_items.",
			InputSchema: map[string]any{
				"type":                 "object",
				"additionalProperties": false,
				"properties": map[string]any{
					"query":       map[string]any{"type": "string"},
					"collections": map[string]any{"type": "array", "minItems": 1, "items": map[string]any{"type": "string", "enum": []string{"budget_items"}}},
					"filters":     filters,
					"limit":       map[string]any{"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
				},
			},
		},
		{
			Name:        BudgetSummary,
			Description: "Сумма листьев ветки бюджета. remain_free из индекса, без пересчёта.",
			InputSchema: map[string]any{
				"type":                 "object",
				"additionalProperties": false,
				"properties": map[string]any{
					"year":           map[string]any{"type": "integer"},
					"article_code":   map[string]any{"type": "string"},
					"article_name":   map[string]any{"type": "string"},
					"match_key":      map[string]any{"type": "string"},
					"expense_kind":   map[string]any{"type": "string", "enum": []string{"production", "management"}},
					"group_by_level": map[string]any{"type": "integer", "minimum": 1, "maximum": 5},
					"limit":          map[string]any{"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
				},
			},
		},
		{
			Name:        IngestStatus,
			Description: "Служебное: число точек, source_file, время последней индексации.",
			InputSchema: map[string]any{
				"type":                 "object",
				"additionalProperties": false,
				"properties":           map[string]any{},
			},
		},
	}
}
