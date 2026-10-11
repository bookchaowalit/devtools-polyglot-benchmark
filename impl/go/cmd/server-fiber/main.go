package main

import (
	"os"

	"github.com/bookchaowalit/polyglot-benchmark-lab/impl/go/lab"
	"github.com/gofiber/fiber/v2"
)

func main() {
	items := lab.LoadItems()
	pool := lab.OpenPool()
	app := fiber.New(fiber.Config{DisableStartupMessage: true})

	app.Get("/health", func(c *fiber.Ctx) error { return c.JSON(fiber.Map{"status": "ok"}) })
	app.Get("/items/:id", func(c *fiber.Ctx) error {
		id, ok := lab.ItemID(c.Params("id"))
		record, found := items[id]
		if !ok || !found {
			return c.Status(404).JSON(fiber.Map{"error": "not_found"})
		}
		return c.JSON(record)
	})
	app.Get("/db/items", func(c *fiber.Ctx) error {
		if pool == nil {
			return c.Status(503).JSON(fiber.Map{"error": "no_database"})
		}
		args := c.Context().QueryArgs()
		a, l, ok := lab.PageParams(string(args.Peek("after")), args.Has("after"), string(args.Peek("limit")), args.Has("limit"))
		if !ok {
			return c.Status(400).JSON(fiber.Map{"error": "bad_request"})
		}
		page, err := lab.FetchPage(c.Context(), pool, a, l)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "db"})
		}
		return c.JSON(page)
	})
	if err := app.Listen("127.0.0.1:" + os.Getenv("PORT")); err != nil {
		panic(err)
	}
}
