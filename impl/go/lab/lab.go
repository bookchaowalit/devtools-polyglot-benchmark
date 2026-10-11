// Package lab holds the data access and validation shared by the Go
// framework variants, so each variant differs from the others only in its
// HTTP framework. The net/http baseline (cmd/server) keeps its own copy of the
// same logic so its numbers stay comparable with earlier runs.
package lab

import (
	"context"
	"encoding/json"
	"os"
	"strconv"

	"github.com/jackc/pgx/v5/pgxpool"
)

const poolSize = 10
const dbQuery = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2"

type Item struct {
	ID         int32    `json:"id"`
	Name       string   `json:"name"`
	PriceCents int32    `json:"price_cents"`
	Qty        int32    `json:"qty"`
	Tags       []string `json:"tags"`
}

type Page struct {
	Items []Item `json:"items"`
}

// LoadItems keeps each record as a decoded object, serialized per request.
func LoadItems() map[int]any {
	data, err := os.ReadFile(os.Getenv("RECORDS_PATH"))
	if err != nil {
		panic(err)
	}
	var records []map[string]any
	if err := json.Unmarshal(data, &records); err != nil {
		panic(err)
	}
	items := make(map[int]any, len(records))
	for _, r := range records {
		items[int(r["id"].(float64))] = r
	}
	return items
}

// OpenPool returns nil when DATABASE_URL is unset.
func OpenPool() *pgxpool.Pool {
	url := os.Getenv("DATABASE_URL")
	if url == "" {
		return nil
	}
	cfg, err := pgxpool.ParseConfig(url)
	if err != nil {
		panic(err)
	}
	cfg.MinConns, cfg.MaxConns = poolSize, poolSize
	pool, err := pgxpool.NewWithConfig(context.Background(), cfg)
	if err != nil {
		panic(err)
	}
	if err := pool.Ping(context.Background()); err != nil {
		panic(err)
	}
	return pool
}

func FetchPage(ctx context.Context, pool *pgxpool.Pool, after, limit int) (Page, error) {
	out := Page{Items: []Item{}}
	rows, err := pool.Query(ctx, dbQuery, after, limit)
	if err != nil {
		return out, err
	}
	defer rows.Close()
	for rows.Next() {
		var it Item
		if err := rows.Scan(&it.ID, &it.Name, &it.PriceCents, &it.Qty, &it.Tags); err != nil {
			return out, err
		}
		out.Items = append(out.Items, it)
	}
	return out, rows.Err()
}

func digits(raw string) bool {
	if raw == "" {
		return false
	}
	for _, c := range raw {
		if c < '0' || c > '9' {
			return false
		}
	}
	return true
}

// ItemID accepts digits only.
func ItemID(raw string) (int, bool) {
	if !digits(raw) {
		return 0, false
	}
	n, err := strconv.Atoi(raw)
	return n, err == nil
}

// PageParams validates after/limit the same way every lane does.
func PageParams(after string, hasAfter bool, limit string, hasLimit bool) (int, int, bool) {
	a, l := 0, 50
	var err error
	if hasAfter {
		if !digits(after) {
			return 0, 0, false
		}
		if a, err = strconv.Atoi(after); err != nil || a > 1<<31-1 {
			return 0, 0, false
		}
	}
	if hasLimit {
		if !digits(limit) {
			return 0, 0, false
		}
		if l, err = strconv.Atoi(limit); err != nil {
			return 0, 0, false
		}
	}
	return a, l, l >= 1 && l <= 100
}
