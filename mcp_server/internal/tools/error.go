package tools

import (
	"errors"
	"fmt"
)

const (
	kindValidation = "validation"
	kindNotFound   = "not_found"
)

// Error — валидация или неизвестный tool. Не путать с пустым поиском.
type Error struct {
	Kind string
	Msg  string
}

func (e *Error) Error() string {
	if e == nil {
		return ""
	}
	return e.Kind + ": " + e.Msg
}

func validationError(format string, args ...any) error {
	return &Error{Kind: kindValidation, Msg: fmt.Sprintf(format, args...)}
}

func notFoundError(format string, args ...any) error {
	return &Error{Kind: kindNotFound, Msg: fmt.Sprintf(format, args...)}
}

// IsValidation — невалидный вход, не «ничего не нашли».
func IsValidation(err error) bool {
	var e *Error
	return errors.As(err, &e) && e.Kind == kindValidation
}

// IsNotFound — tool не зарегистрирован (в т.ч. get_contract).
func IsNotFound(err error) bool {
	var e *Error
	return errors.As(err, &e) && e.Kind == kindNotFound
}
