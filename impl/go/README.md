# Lane: go-nethttp

- Go (version pinned in `go.mod`), stdlib `encoding/json`, `crypto/sha256`, `net/http`
- Records are kept as decoded objects and serialized per request, like the other lanes

```bash
cd impl/go && go build -o bin/ ./cmd/...
```
