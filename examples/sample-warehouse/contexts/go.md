# Go Standards

Go-specific conventions for all Go projects.

---

## Error Handling

**Brief:** Always handle errors explicitly. Never ignore an error with `_`.

```go
// Correct
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}

// Avoid
result, _ := doSomething()
```

Wrap errors with `%w` to preserve the chain. Use `errors.Is` / `errors.As` to inspect wrapped errors.

---

## Interfaces

**Brief:** Define interfaces at the point of use (consumer side), not at the point of implementation.

Keep interfaces small — prefer single-method interfaces.

```go
// Correct — defined where it's consumed
type Notifier interface {
    Notify(ctx context.Context, msg string) error
}

func NewAlertService(n Notifier) *AlertService { ... }
```

---

## Naming

**Brief:** Follow Go naming conventions strictly.

- Exported: `PascalCase`
- Unexported: `camelCase`
- Acronyms: `HTTPServer`, `userID`, `parseURL`
- Avoid stutter: `user.UserName` → `user.Name`

---

## Formatting

**Brief:** All code must be formatted with `gofmt` / `goimports`. No exceptions — CI enforces this.

```bash
goimports -w .
```

---

## Concurrency

**Brief:** Document goroutine ownership and lifetime. Always think about cancellation.

- Pass `context.Context` as the first argument to functions that do I/O or long work
- Use `errgroup` for managing multiple goroutines
- Prefer channels for signalling, mutexes for shared state

---

## Package Structure

**Brief:** Flat is fine for small services. Avoid deep nesting. Package names are lowercase, single words.

Standard layout for services:
```
cmd/        # entrypoints (main packages)
internal/   # private application code
pkg/        # reusable library code (if any)
```
