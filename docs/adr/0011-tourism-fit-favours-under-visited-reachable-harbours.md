# Tourism fit: favour harbours that visitors can reach but that are not crowded

Community was (boats + tourist access) ÷ 2, with tourist access rising with the number of places to stay. That rewards the busiest resorts, the opposite of what pescatourism is for: spreading visitors to quiet harbours. We split it: Community is boats only, and a new factor joins the product.

Tourism fit = Enough visitors × Reachable × Not crowded, on fixed scales (never divided by the best harbour):
- Enough visitors = min(1, places to stay within 10 km ÷ 10). One boat needs about 800 customers a year, so a small floor is enough.
- Reachable = 1 up to 5 km from an airport or ferry port (OSM), then 1 / (1 + (km − 5) / 10). Big gateways are not penalised; crowding is measured directly.
- Not crowded = 1 / (1 + guest nights per resident a year ÷ 20), from the harbour's municipality (`tourism.py`): Azores from INE municipal nights; South Aegean from ELSTAT 2024 island-group nights scaled to Eurostat 2025 and split by Inside Airbnb beds, plus Airbnb reviews × the NUTS 3 platform nights per review. Pilot harbours only.

## Consequences
- Greek resort islands drop sharply: Mykonos (315 nights per resident) gets Not crowded 0.06, Syros (29) 0.41, Vila Franca do Campo (3.6) 0.85.
- Harbours outside the pilot get Enough visitors × Reachable only, like the other partial factors.
- The Greek split by rental beds is an estimate; Symi and Kastelorizo are likely too high.
- Bands (Under-visited < 10, Balanced < 50, Busy < 150, Crowded) are labels only; the score uses the smooth curve.
