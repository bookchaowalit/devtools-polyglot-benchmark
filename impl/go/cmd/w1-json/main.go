package main

import (
	"encoding/json"
	"os"
	"sort"
)

type item struct {
	ID         int      `json:"id"`
	Name       string   `json:"name"`
	PriceCents int64    `json:"price_cents"`
	Qty        int64    `json:"qty"`
	Tags       []string `json:"tags"`
}

type summary struct {
	Count           int            `json:"count"`
	TotalValueCents int64          `json:"total_value_cents"`
	ByTag           map[string]int `json:"by_tag"`
	Top5            []int          `json:"top5"`
}

func main() {
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	var records []item
	if err := json.Unmarshal(data, &records); err != nil {
		panic(err)
	}
	out := summary{Count: len(records), ByTag: map[string]int{}}
	for _, r := range records {
		out.TotalValueCents += r.PriceCents * r.Qty
		for _, t := range r.Tags {
			out.ByTag[t]++
		}
	}
	ranked := make([]item, len(records))
	copy(ranked, records)
	sort.Slice(ranked, func(i, j int) bool {
		vi, vj := ranked[i].PriceCents*ranked[i].Qty, ranked[j].PriceCents*ranked[j].Qty
		if vi != vj {
			return vi > vj
		}
		return ranked[i].ID < ranked[j].ID
	})
	for _, r := range ranked[:min(5, len(ranked))] {
		out.Top5 = append(out.Top5, r.ID)
	}
	enc := json.NewEncoder(os.Stdout)
	if err := enc.Encode(out); err != nil { // map keys are encoded in sorted order
		panic(err)
	}
}
