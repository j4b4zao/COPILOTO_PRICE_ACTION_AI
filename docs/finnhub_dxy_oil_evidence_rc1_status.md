# Finnhub DXY/OIL Evidence RC1 — Status

Date: 2026-10-06

## Catalog evidence

Real Finnhub Forex catalog exposed:
- DXY candidate CAPITAL:DXY — description: US Dollar Index
- OIL candidate OANDA:WTICO_USD — description: Oanda West Texas Oil

These are provider-catalog identities, not approved router mappings.

## Real quote probe

- CAPITAL:DXY -> HTTP 403
- OANDA:WTICO_USD -> HTTP 403

No valid quote payload or timestamp was obtained.

## Interpretation

The identities are not rejected merely because the quote endpoint returned 403:
the provider catalog itself exposed them. However, current account access did
not demonstrate usable quote availability, so neither asset is eligible for
transport/configuration/router promotion.

## Safety

- observational evidence only
- no ProviderSymbolMap created
- no manifest created
- no router route created
- no Bot integration
- no operational influence
- no proxy substitution

## Remaining coverage

Provider-evidenced and quote-demonstrated:
- US500 -> FMP ^GSPC
- NASDAQ -> FMP ^IXIC
- VIX -> FMP ^VIX
- GOLD -> Twelve Data XAU/USD (timestamp normalization still unresolved)

Still unresolved for usable intraday collection:
- DXY
- OIL
- US10Y

Next work should evaluate an alternate provider/data source for these assets,
with identity and intraday timestamp evidence before promotion.
