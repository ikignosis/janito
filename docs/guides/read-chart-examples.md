# 📊 Read Chart Tool Examples

The `read_chart` tool allows you to display various types of charts and data visualizations directly in the terminal using the rich library.

## Chart Types

### 1. Table Charts

Display data in a formatted table:

```json
{
  "type": "table",
  "data": [
    {"name": "Alice", "age": 30, "department": "Engineering"},
    {"name": "Bob", "age": 25, "department": "Marketing"},
    {"name": "Charlie", "age": 35, "department": "Sales"}
  ]
}
```

### 2. Bar Charts

Display categorical data as horizontal bars:

```json
{
  "type": "bar",
  "data": {
    "January": 150,
    "February": 200,
    "March": 175,
    "April": 225
  }
}
```

### 3. Pie Charts

Display proportional data as pie segments:

```json
{
  "type": "pie",
  "data": {
    "Desktop": 45,
    "Mobile": 30,
    "Tablet": 15,
    "Other": 10
  }
}
```

### 4. Line Charts

Display trends over time or continuous data:

```json
{
  "type": "line",
  "data": [
    {"month": 1, "revenue": 10000},
    {"month": 2, "revenue": 12000},
    {"month": 3, "revenue": 9500},
    {"month": 4, "revenue": 14000}
  ]
}
```

## Usage Examples

### Basic Usage

```python
# Simple table
read_chart(
    data={"type": "table", "data": [{"product": "Laptop", "price": 999}, {"product": "Mouse", "price": 25}]},
    title="Product Catalog"
)

# Sales data bar chart
read_chart(
    data={"type": "bar", "data": {"2023": 50000, "2024": 75000}},
    title="Annual Sales",
    width=100
)
```

### Advanced Usage

```python
# Complex pie chart with custom dimensions
read_chart(
    data={
        "type": "pie",
        "data": {
            "AWS": 40,
            "Azure": 30,
            "GCP": 20,
            "Others": 10
        }
    },
    title="Cloud Provider Market Share",
    width=120,
    height=25
)

# Multi-series line chart
read_chart(
    data={
        "type": "line",
        "data": [
            {"period": "Q1", "sales": 100, "expenses": 80},
            {"period": "Q2", "sales": 120, "expenses": 90},
            {"period": "Q3", "sales": 110, "expenses": 85},
            {"period": "Q4", "sales": 140, "expenses": 100}
        ]
    },
    title="Quarterly Performance"
)
```

## Data Formats

### Dictionary Format
For simple key-value data:

```json
{
  "type": "bar",
  "data": {
    "Category A": 100,
    "Category B": 150,
    "Category C": 75
  }
}
```

### List of Records Format
For structured data with multiple fields:

```json
{
  "type": "table",
  "data": [
    {"country": "USA", "population": 331000000, "gdp": 21427700},
    {"country": "China", "population": 1439323776, "gdp": 14342900},
    {"country": "Japan", "population": 126476461, "gdp": 5081770}
  ]
}
```

## Error Handling

The tool provides helpful error messages:

- **Missing data**: "⚠️ Warning: No data provided for chart"
- **Invalid type**: "❌ Error: Unsupported chart type 'xyz'. Use: table, bar, line, pie"
- **Import issues**: "❌ Error: rich library not available for chart display"

## Integration with Janito

When using Janito in chat mode, you can ask it to create visualizations:

```
User: Show me a chart of the quarterly sales data
Janito: I'll create a bar chart for you...
[Uses read_chart tool to display the visualization]
```

## Best Practices

1. **Data Validation**: Ensure your data is properly formatted JSON
2. **Appropriate Chart Types**: Choose the right chart type for your data
3. **Titles**: Always provide descriptive titles
4. **Dimensions**: Adjust width/height for better readability
5. **Data Types**: Use numeric values for bar, pie, and line charts