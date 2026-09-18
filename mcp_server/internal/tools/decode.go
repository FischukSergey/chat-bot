package tools

import (
	"bytes"
	"encoding/json"
	"strings"
)

func decodeStrict(raw json.RawMessage, dest any) error {
	if len(bytes.TrimSpace(raw)) == 0 {
		raw = []byte("{}")
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(dest); err != nil {
		msg := err.Error()
		if strings.Contains(msg, "unknown field") {
			return validationError("%s", msg)
		}
		return validationError("невалидный JSON: %s", msg)
	}
	return nil
}
