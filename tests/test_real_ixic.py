from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)

discovery = TwelveDataSymbolDiscovery()

result = discovery.search("COMP")

print("STATUS :", discovery.last_status)
print("ERROR  :", discovery.last_error)
print("COUNT  :", len(result))

for item in result:
    print(item)