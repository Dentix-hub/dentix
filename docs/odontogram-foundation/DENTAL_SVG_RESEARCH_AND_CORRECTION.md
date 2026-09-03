# Dental SVG Research and Corrective Rendering Rules

Date: `2026-08-29`

## Why this research was required

The first A5 preview did not extend the existing Dentix odontogram. It rendered a separate specimen page and used hand-estimated root-family paths. User review rejected both the changed chart presentation and the anatomical quality. Those visuals are not accepted evidence.

## Evidence reviewed

### External dental morphology

1. The systematic review of permanent premolars reports that maxillary first premolars are split almost evenly between one and two roots, while maxillary second and mandibular premolars are predominantly single-rooted. A renderer therefore needs a canonical default plus explicit variation capability; it must not present one template as universal truth.
   - https://pmc.ncbi.nlm.nih.gov/articles/PMC11149329/
2. CBCT research on maxillary first molars reports the usual three distinct roots and identifies them as mesiobuccal, distobuccal, and palatal; uncommon variants also exist.
   - https://pmc.ncbi.nlm.nih.gov/articles/PMC4476355/
   - https://pmc.ncbi.nlm.nih.gov/articles/PMC9408299/
3. Reviews of mandibular molars support the canonical two-root model (mesial and distal) while documenting complex canal and curvature variation.
   - https://pubmed.ncbi.nlm.nih.gov/37248469/
   - https://pmc.ncbi.nlm.nih.gov/articles/PMC7030962/
4. Micro-CT and CBCT studies of primary molars support three roots as the common maxillary pattern and two roots as the common mandibular pattern, with complex canals and possible fusion.
   - https://pubmed.ncbi.nlm.nih.gov/24563173/
   - https://pubmed.ncbi.nlm.nih.gov/35946238/
   - https://pubmed.ncbi.nlm.nih.gov/32100200/
5. Primary mandibular successor research confirms that the permanent premolar develops between the roots of its primary predecessor. The schematic primary molar therefore needs slender, separated/divergent roots rather than scaled permanent-molar roots.
   - https://pmc.ncbi.nlm.nih.gov/articles/PMC9324923/

### Standards and rendering references

1. HL7's FDI surface terminology defines stable semantic surface codes (`M`, `O`, `I`, `D`, `B`, `V`, `L`). Geometry must map to these semantics rather than inventing UI-only names.
   - https://build.fhir.org/ig/HL7/UTG/en/CodeSystem-FDI-surface.html
2. SVG 2 defines `viewBox` as the coordinate-system boundary and `preserveAspectRatio` as the scaling contract. Crown and root layers must share one local coordinate system; arbitrary transforms between unrelated view boxes are not acceptable.
   - https://www.w3.org/TR/SVG/coords.html
3. SVG 2 hit-testing depends on painted geometry, clipping, and `pointer-events`. Invisible interaction paths must be intentional and separate from the visible anatomy.
   - https://www.w3.org/TR/SVG/interact.html
4. `react-odontogram` demonstrates a useful implementation pattern: per-tooth structured vector records with separate outline, shadow, and highlight paths plus stable notation metadata. It is an engineering reference, not an anatomical authority and not a source to copy without license review.
   - https://github.com/biomathcode/react-odontogram

## Corrected architecture rule

The existing Dentix odontogram is the immutable visual baseline. The correction must:

1. Render the existing chart component and its current row/quadrant layout.
2. Preserve every existing crown path, crown transform, tooth order, label, spacing, shell, and interaction.
3. Add a `root` SVG group behind each existing crown inside the same tooth component.
4. Extend only the local SVG canvas needed to reveal roots; do not replace the chart or the crowns.
5. Use per-FDI anatomy records. Family templates may provide controlled defaults, but every tooth key must resolve explicitly and may override curvature, length, divergence, and root count.
6. Treat root count/shape as a canonical schematic default, not a diagnosis of a patient's actual anatomy.

## Geometry rules learned from the review

- Use one canonical coordinate system per tooth; no scaling a `50 × 60` crown into an unrelated `100 × 160` root canvas.
- Record the cemento-enamel/cervical join as explicit left/right anchors. Root paths must begin and end at those anchors with no gap or overlap into the crown body.
- Use smooth cubic Bézier contours with tangent continuity at the cervical join and apex; avoid triangular spikes and parallel capsule shapes.
- Incisors and canines use one tapered root with tooth-specific length and a subtle apical curvature, not one identical path.
- Maxillary first premolars default to two roots in the schematic but keep an explicit one-root variation; other premolars default to one root.
- Maxillary molars use three named roots; the palatal root is not drawn as a third equal buccal spike.
- Mandibular molars use mesial and distal roots with controlled divergence/curvature.
- Primary molar roots are slender and more separated around the successor space; they are not merely shorter permanent roots.
- Left/right counterparts may share a base definition only through a tested mirror transform. Upper/lower teeth require distinct geometry, not vertical scaling.

## Mandatory visual acceptance test

For every representative tooth family, capture a same-size overlay:

- baseline: existing Dentix tooth/chart;
- candidate: baseline plus roots;
- crown-difference mask: must contain zero changed crown pixels;
- new-pixel mask: must be confined to the root extension region except for the cervical join;
- full-mouth view: row order, spacing, labels, shell, and interactions unchanged.

No root phase may return to `PASS` until the user approves the real-chart comparison, not a standalone specimen.
