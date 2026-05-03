# React Standards

React-specific conventions for all frontend projects.

---

## Functional Components Only

**Brief:** Use functional components with hooks. No class components.

```tsx
// Correct
function UserCard({ user }: { user: User }) {
  return <div>{user.name}</div>;
}

// Avoid
class UserCard extends React.Component { ... }
```

---

## Component Structure

**Brief:** One component per file. Filename matches component name.

Order within a component file:
1. Imports
2. Types/interfaces
3. Component function
4. Helper functions (if small and only used here)
5. Styles (if co-located)

---

## Hooks

**Brief:** Prefer built-in hooks. Extract reusable stateful logic into custom hooks (`use` prefix).

```typescript
// Extract complex logic into a custom hook
function useUserData(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // ...
  return { user, loading };
}
```

- Never call hooks conditionally
- Keep `useEffect` dependencies accurate — don't suppress linter warnings

---

## Props

**Brief:** Define prop types explicitly. Avoid spreading unknown props onto DOM elements.

```tsx
interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

function Button({ label, onClick, disabled = false }: ButtonProps) { ... }
```

---

## State Management

**Brief:** Start with local state (`useState`). Lift state only when necessary. Reach for external state management (Zustand, Jotai) only when prop drilling becomes a real problem.

---

## Keys

**Brief:** Always use stable, unique keys in lists. Never use array index as key when the list can reorder.

```tsx
// Correct
items.map(item => <Row key={item.id} item={item} />)

// Avoid
items.map((item, i) => <Row key={i} item={item} />)
```
