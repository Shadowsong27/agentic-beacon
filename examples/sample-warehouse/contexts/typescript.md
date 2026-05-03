# TypeScript Standards

TypeScript-specific conventions for all TS/JS projects.

---

## Strict Mode

**Brief:** Always enable strict mode in `tsconfig.json`. No exceptions.

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

---

## No `any`

**Brief:** Never use `any`. Use `unknown` when the type is genuinely unknown, then narrow it.

```typescript
// Correct
function parse(input: unknown): string {
  if (typeof input !== "string") throw new Error("Expected string");
  return input;
}

// Avoid
function parse(input: any): string {
  return input;
}
```

---

## Schema Validation

**Brief:** Use `zod` for all runtime validation of external data (API responses, env vars, form input).

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
});

type User = z.infer<typeof UserSchema>;
```

---

## Null Handling

**Brief:** Prefer `undefined` over `null` in your own code. Handle both when dealing with external APIs.

Use optional chaining (`?.`) and nullish coalescing (`??`) over manual null checks.

```typescript
const name = user?.profile?.name ?? "Anonymous";
```

---

## Imports

**Brief:** Use named exports. Avoid default exports — they make refactoring harder.

```typescript
// Correct
export function calculateTotal() { ... }
export type { OrderSummary };

// Avoid
export default function calculateTotal() { ... }
```

---

## Async / Await

**Brief:** Always use `async/await` over raw Promise chains. Always handle errors with `try/catch`.

```typescript
async function fetchUser(id: string): Promise<User> {
  try {
    const res = await api.get(`/users/${id}`);
    return UserSchema.parse(res.data);
  } catch (err) {
    throw new UserFetchError(`Failed to fetch user ${id}`, { cause: err });
  }
}
```
