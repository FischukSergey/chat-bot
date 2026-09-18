package tools

import (
	"context"
	"encoding/json"
	"slices"
)

type statusIn struct{}

func (h *Handler) ingestStatus(ctx context.Context, raw json.RawMessage) (StatusResult, error) {
	var in statusIn
	if err := decodeStrict(raw, &in); err != nil {
		return StatusResult{}, err
	}
	n, err := h.qd.Count(ctx, h.cfg.Collection, nil)
	if err != nil {
		return StatusResult{}, err
	}
	points, err := h.qd.ScrollAll(ctx, h.cfg.Collection, nil, 256)
	if err != nil {
		return StatusResult{}, err
	}
	files := map[string]struct{}{}
	var last *string
	for _, p := range points {
		if sf := payloadString(p.Payload, "source_file", ""); sf != "" {
			files[sf] = struct{}{}
		}
		if at := payloadString(p.Payload, "indexed_at", ""); at != "" {
			if last == nil || at > *last {
				cp := at
				last = &cp
			}
		}
	}
	names := make([]string, 0, len(files))
	for f := range files {
		names = append(names, f)
	}
	slices.Sort(names)
	return StatusResult{
		Collections: []CollectionStatus{{
			Name:          h.cfg.Collection,
			Points:        n,
			SourceFiles:   names,
			LastIndexedAt: last,
		}},
	}, nil
}
