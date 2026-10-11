package main

import (
	"os"

	"github.com/bookchaowalit/polyglot-benchmark-lab/impl/go/lab"
	"github.com/gin-gonic/gin"
)

func main() {
	items := lab.LoadItems()
	pool := lab.OpenPool()
	gin.SetMode(gin.ReleaseMode)
	r := gin.New() // no logger, like the other lanes

	r.GET("/health", func(c *gin.Context) { c.JSON(200, gin.H{"status": "ok"}) })
	r.GET("/items/:id", func(c *gin.Context) {
		id, ok := lab.ItemID(c.Param("id"))
		record, found := items[id]
		if !ok || !found {
			c.JSON(404, gin.H{"error": "not_found"})
			return
		}
		c.JSON(200, record)
	})
	r.GET("/db/items", func(c *gin.Context) {
		if pool == nil {
			c.JSON(503, gin.H{"error": "no_database"})
			return
		}
		after, hasAfter := c.GetQuery("after")
		limit, hasLimit := c.GetQuery("limit")
		a, l, ok := lab.PageParams(after, hasAfter, limit, hasLimit)
		if !ok {
			c.JSON(400, gin.H{"error": "bad_request"})
			return
		}
		page, err := lab.FetchPage(c.Request.Context(), pool, a, l)
		if err != nil {
			c.JSON(500, gin.H{"error": "db"})
			return
		}
		c.JSON(200, page)
	})
	if err := r.Run("127.0.0.1:" + os.Getenv("PORT")); err != nil {
		panic(err)
	}
}
