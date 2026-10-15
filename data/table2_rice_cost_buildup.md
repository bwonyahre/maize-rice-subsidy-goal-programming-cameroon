# Rice input cost table — full reconstruction

Source for every line item: Task-force Riz, MINADER/JICA, *Analyse de la compétitivité
de la filière riz au Cameroun* (2021), field-data cost tables for the rainfed and
irrigated systems (UNVDA and SEMRY survey data). Only the "input" line items
(subsidizable by the 2019 Manual of Procedures: seed, fertilizer, herbicide/nursery) are
retained; labor, transport and — for irrigated rice — infrastructure development/
amortization are excluded, for comparability with the maize package (which likewise
excludes labor).

| Line item | Rainfed (FCFA/ha) | Irrigated, existing infrastructure (FCFA/ha) |
|---|---|---|
| Improved seed | 107,143 | 12,500 |
| NPK | 60,000 | 68,000 |
| Urea | 28,000 | 36,000 |
| Herbicide / nursery | — (not itemized for rainfed in JICA source) | 19,000 |
| **Total inputs / ha** | **195,143** | **135,500** |

## Why the seed cost differs by a factor of ~8.6 between systems

This gap (107,143 vs 12,500 FCFA/ha) needs explicit
justification, not just a number. It reflects two *structurally different seed
economies* in the JICA source, not a data error:

1. **Seeding method and rate.** Rainfed rice in Cameroon is direct-seeded at a high rate
   (broadcasting or dense line-sowing, commonly 60–80 kg/ha of seed) because it must
   compensate for uneven germination, weed competition and the absence of water control.
   Irrigated systems (SEMRY, UNVDA, Lagdo) are transplanted from a nursery: nursery beds
   use a much lower seed rate per hectare of transplanted field (typically 25–35 kg/ha
   nursery-equivalent), so fewer kilograms of seed are purchased per hectare of final
   field — the nursery/transplanting labor cost is itself captured separately (and
   excluded here, along with all labor).
2. **Seed renewal cycle and source.** Rainfed farmers in the JICA survey areas
   predominantly purchase certified seed each season (no retained seed, higher
   effective unit cost per hectare), whereas the irrigated schemes included in the
   study benefit from scheme-level seed multiplication and distribution (SEMRY/UNVDA
   extension services), lowering the per-hectare cash cost captured in the
   competitiveness study.

This explanation is drawn from the JICA study's own system descriptions; it is **not**
independently re-verified against primary field data by the present authors, and the
manuscript states this explicitly as a limitation: the line-item gap is
internally consistent with the JICA source's stated system differences, but a
region-specific validation (e.g., direct interviews with SEMRY/UNVDA input-supply
offices) was outside the scope of this study.

## Ceiling yields used in the model

- Rainfed: 3.75 t/ha (JICA sensitivity scenario raising 3.0 → 3.5 t/ha, extended
  modestly to remain inside the study's own sensitivity range)
- Irrigated: 6.5 t/ha (JICA sensitivity scenario raising 6.0 → 6.5 t/ha)

Both remain inside the yield range documented for NERICA and irrigated varieties
elsewhere in the literature (3–9 t/ha depending on conditions).
