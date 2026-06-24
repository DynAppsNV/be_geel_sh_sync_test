Customises analytic distribution on accounting documents.

- Shows the amount column (alongside the percentage) on the analytic distribution
  widget of journal items, using the line balance as the reference amount.
- Raises the **Percentage Analytic** decimal precision from the Odoo default of 2 to
  6 decimal places. Distribution percentages are rounded to this precision
  server-side on every save, so with too few decimals an amount entered on a line
  drifts on reload (e.g. 9.99 → 9.96 on a 1200 balance). The round-trip resolution is
  ``balance × 10⁻⁽ᵈⁱᵍⁱᵗˢ⁺²⁾``, so 6 decimals keep the entered amount cent-exact for
  balances up to ~€1,000,000 (4 decimals still drifted a cent on mid-size balances,
  e.g. €5,761.06 on a €14,402.67 line) while still allowing percentages to be entered
  directly.
