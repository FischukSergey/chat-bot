package qdrant

// BudgetFilter — фильтры сметы из docs/api-sprint-3.md. Поля договоров сюда не входят.
type BudgetFilter struct {
	Year         *int
	ExpenseKind  string
	ArticleCode  string
	ArticleName  string
	MatchKey     string
	AncestorCode string
	AmountMin    *float64
	AmountMax    *float64
}

// Filter — тело filter Qdrant (must).
type Filter struct {
	Must []Condition `json:"must,omitempty"`
}

// Condition — match по keyword или range по числу.
type Condition struct {
	Key   string    `json:"key"`
	Match *Match    `json:"match,omitempty"`
	Range *NumRange `json:"range,omitempty"`
}

// Match — точное значение (в т.ч. элемент массива ancestor_codes).
type Match struct {
	Value any `json:"value"`
}

// NumRange — диапазон limit_amount.
type NumRange struct {
	Gte *float64 `json:"gte,omitempty"`
	Lte *float64 `json:"lte,omitempty"`
}

// BuildFilter собирает Qdrant filter. Пустой фильтр → nil (не {} с пустым must).
func BuildFilter(f BudgetFilter) *Filter {
	var must []Condition
	if f.Year != nil {
		must = append(must, match("year", *f.Year))
	}
	if f.ExpenseKind != "" {
		must = append(must, match("expense_kind", f.ExpenseKind))
	}
	if f.ArticleCode != "" {
		must = append(must, match("article_code", f.ArticleCode))
	}
	if f.ArticleName != "" {
		must = append(must, match("article_name", f.ArticleName))
	}
	if f.MatchKey != "" {
		must = append(must, match("match_key", f.MatchKey))
	}
	if f.AncestorCode != "" {
		must = append(must, match("ancestor_codes", f.AncestorCode))
	}
	if f.AmountMin != nil || f.AmountMax != nil {
		must = append(must, Condition{
			Key:   "limit_amount",
			Range: &NumRange{Gte: f.AmountMin, Lte: f.AmountMax},
		})
	}
	if len(must) == 0 {
		return nil
	}
	return &Filter{Must: must}
}

func match(key string, value any) Condition {
	return Condition{Key: key, Match: &Match{Value: value}}
}
