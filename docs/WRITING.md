# Write your own toolkit

A toolkit is a subclass of `BaseToolkit` whose public methods are marked
with `@tool`. Configuration lives on the instance; tool methods read it
through `self`.

```python
from pydantic_ai_toolkits import BaseToolkit, tool


class WeatherToolkit(BaseToolkit):
    """Look up current weather for a configurable provider."""

    def __init__(self, api_key: str, units: str = "metric") -> None:
        self.api_key = api_key
        self.units = units
        super().__init__()                # MUST be last — it scans @tool methods

    @tool
    def current_temperature(self, city: str) -> float:
        """Return the current temperature for a city in the configured units."""
        ...
```

## Rules

1. Subclass `BaseToolkit`.
2. Configure `self.*` in `__init__`, then call `super().__init__()` as the
   last statement.
3. Decorate every method you want to expose with `@tool`. Use
   `@tool(takes_ctx=True)` if the first method argument (after `self`) is
   a `RunContext[Deps]`.
4. Type-hint every parameter. pydantic-ai derives the JSON schema from
   the method signature.
5. Keep toolkits independent. Do not import another toolkit module from
   yours. Lazy-import third-party libraries so the module is importable
   without the extra installed.

## Method → tool mapping

| Method element            | Becomes               |
|---------------------------|-----------------------|
| name                      | tool name             |
| docstring                 | tool description      |
| parameter type hints      | tool input schema     |
| return type hint          | tool output schema    |
| `@tool(name=...)`         | overrides tool name   |
| `@tool(description=...)`  | overrides description |
| `@tool(takes_ctx=True)`   | injects RunContext    |
