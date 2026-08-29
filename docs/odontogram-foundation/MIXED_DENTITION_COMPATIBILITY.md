# Mixed Dentition Compatibility

## Canonical identity

The anatomy registry uses string FDI keys. Permanent teeth occupy quadrants `1–4` and primary teeth occupy quadrants `5–8`, so all 52 registered positions remain unique when both dentitions are present in one chart instance.

Examples:

- permanent upper-right central incisor: `11`;
- primary upper-right central incisor: `51`;
- permanent lower-left first molar: `36`;
- primary lower-left second molar: `75`.

## Coexistence rule

A mixed-dentition Projection DTO supplies an explicit ordered list of tooth keys. The renderer resolves each key independently from the same registry and must not infer that selecting one dentition removes the other. Layout slots, eruption/lifecycle state, and visibility are projection concerns; anatomy records remain immutable.

## Notation rule

FDI is the stable internal anatomy identity for this foundation. A later notation adapter may display FDI, Universal, or Palmer labels without changing registry keys, interaction targets, or stored projection references.

## Safety boundary

The presence of permanent and primary teeth in a demo fixture is visual state only. It must not be interpreted as a diagnosis, eruption schedule, or production clinical record.

