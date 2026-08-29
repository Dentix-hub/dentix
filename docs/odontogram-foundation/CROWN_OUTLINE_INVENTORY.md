# Current Dentix Crown Outline Inventory

Inventory date: `2026-08-29`

## Production chart

### `frontend/src/features/dental/DentalChartSVG.jsx`

- Active in `PatientDetails.jsx` for adult and pediatric chart views.
- Contains minimalist family-level SVG paths for molars, premolars, canines, and incisors.
- Uses white enamel, slate outline, simple internal fissure lines, and a compact `50 × 60` view box.
- Uses Universal `1–32` / primary `A–T` positions and converts selection data to FDI.

## Existing detailed programmatic geometry

### `frontend/src/features/dental/v3/assets/dentalPaths.js`

- Exports `getOrganicToothType(number)` for all 32 permanent Universal positions.
- Each resolved record contains a root path plus a `CrownBox` surface map.
- CrownBox exposes `Occlusal`, `Buccal`, `Lingual`, `Mesial`, and `Distal` path segments where applicable.
- Mirror/copy references already reduce duplicate geometry.

### `frontend/src/features/dental/v3/components/AdvancedTooth.jsx`

- Demonstrates current programmatic layer order: roots, crown body, surfaces, status overlays.
- Uses white enamel, `#cbd5e1` surface outlines, subtle shadows, and simple solid clinical colors.
- Is not currently the production chart entry in `PatientDetails.jsx`.

## Experimental reference only

### `frontend/src/features/clinical-chart-v2/`

- Uncommitted pre-A0 experiment containing transparent raster teeth and programmatic tooth-46 effects.
- Preserved for visual reference only; it is not the canonical Part I renderer or anatomy schema.

## Normalization decision

`frontend/src/features/clinical-chart/rendering/crownGeometry.js` is the canonical Part I access adapter:

- callers request geometry by stable FDI anatomy key;
- permanent teeth resolve to the existing detailed Dentix `CrownBox` paths;
- primary teeth resolve to the same family-level path language used by the current production chart;
- source path strings and source style tokens remain unchanged;
- notation conversion and ad hoc source imports stay outside renderer components.

