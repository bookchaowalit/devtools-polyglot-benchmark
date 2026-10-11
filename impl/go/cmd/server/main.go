package main

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"strconv"

	"github.com/jackc/pgx/v5/pgxpool"
)

const poolSize = 10
const dbQuery = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2"

type dbItem struct {
	ID         int32    `json:"id"`
	Name       string   `json:"name"`
	PriceCents int32    `json:"price_cents"`
	Qty        int32    `json:"qty"`
	Tags       []string `json:"tags"`
}

func intParam(r *http.Request, name string, fallback int) (int, bool) {
	raw := r.URL.Query().Get(name)
	if !r.URL.Query().Has(name) {
		return fallback, true
	}
	for _, c := range raw {
		if c < '0' || c > '9' {
			return 0, false
		}
	}
	n, err := strconv.Atoi(raw)
	return n, err == nil
}

func writeJSON(w http.ResponseWriter, status int, body []byte) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(body)
}

func main() {
	data, err := os.ReadFile(os.Getenv("RECORDS_PATH"))
	if err != nil {
		panic(err)
	}
	var records []json.RawMessage
	if err := json.Unmarshal(data, &records); err != nil {
		panic(err)
	}
	// Records are stored pre-encoded, the same way the other lanes keep
	// parsed objects in memory and let the framework serialize them.
	items := make(map[int]any, len(records))
	for _, raw := range records {
		var r map[string]any
		if err := json.Unmarshal(raw, &r); err != nil {
			panic(err)
		}
		items[int(r["id"].(float64))] = r
	}
	notFound := []byte(`{"error":"not_found"}`)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, 200, []byte(`{"status":"ok"}`))
	})
	mux.HandleFunc("GET /items/{id}", func(w http.ResponseWriter, r *http.Request) {
		raw := r.PathValue("id")
		id, err := strconv.Atoi(raw)
		record, ok := items[id]
		if err != nil || raw[0] < '0' || raw[0] > '9' || !ok {
			writeJSON(w, 404, notFound)
			return
		}
		body, _ := json.Marshal(record)
		writeJSON(w, 200, body)
	})
	var pool *pgxpool.Pool
	if url := os.Getenv("DATABASE_URL"); url != "" {
		cfg, err := pgxpool.ParseConfig(url)
		if err != nil {
			panic(err)
		}
		cfg.MinConns, cfg.MaxConns = poolSize, poolSize
		if pool, err = pgxpool.NewWithConfig(context.Background(), cfg); err != nil {
			panic(err)
		}
		if err := pool.Ping(context.Background()); err != nil {
			panic(err)
		}
	}
	mux.HandleFunc("GET /db/items", func(w http.ResponseWriter, r *http.Request) {
		if pool == nil {
			writeJSON(w, 503, []byte(`{"error":"no_database"}`))
			return
		}
		after, okA := intParam(r, "after", 0)
		limit, okL := intParam(r, "limit", 50)
		if !okA || !okL || limit < 1 || limit > 100 {
			writeJSON(w, 400, []byte(`{"error":"bad_request"}`))
			return
		}
		rows, err := pool.Query(r.Context(), dbQuery, after, limit)
		if err != nil {
			writeJSON(w, 500, []byte(`{"error":"db"}`))
			return
		}
		defer rows.Close()
		out := struct {
			Items []dbItem `json:"items"`
		}{Items: []dbItem{}}
		for rows.Next() {
			var it dbItem
			if err := rows.Scan(&it.ID, &it.Name, &it.PriceCents, &it.Qty, &it.Tags); err != nil {
				writeJSON(w, 500, []byte(`{"error":"db"}`))
				return
			}
			out.Items = append(out.Items, it)
		}
		body, _ := json.Marshal(out)
		writeJSON(w, 200, body)
	})
	if err := http.ListenAndServe("127.0.0.1:"+os.Getenv("PORT"), mux); err != nil {
		panic(err)
	}
}
