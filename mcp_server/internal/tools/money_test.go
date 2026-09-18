package tools

import "testing"

func TestSumMoneyNullNotZero(t *testing.T) {
	lim := 1.5
	got := sumMoney([]MoneyFields{
		{Limit: &lim, AmountUnit: "thousand_rub", Currency: "RUB"},
		{Limit: &lim, AmountUnit: "thousand_rub", Currency: "RUB"},
	})
	if got.Limit == nil || *got.Limit != 3 {
		t.Fatalf("limit %+v", got)
	}
	if got.RemainFree != nil || got.Fact != nil {
		t.Fatalf("null стёрли: %+v", got)
	}
}

func TestSumMoneyAllNull(t *testing.T) {
	got := sumMoney([]MoneyFields{{AmountUnit: "thousand_rub", Currency: "RUB"}})
	if got.Limit != nil || got.RemainFree != nil {
		t.Fatalf("%+v", got)
	}
}
