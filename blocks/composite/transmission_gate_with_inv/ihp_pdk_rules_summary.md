# IHP 130nm (SG13G2) Mapped PDK Rules — Summary

This document summarizes the IHP 130nm BiCMOS Open Source PDK rules as they are mapped and used in the **gLayout-IHP130** project, specifically for creating the **transmission gate with inverter** layout.

> [!NOTE]
> The PDK mapping is defined across three files:
> - [ihp130_mapped.py](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/ihp130_mapped/ihp130_mapped.py) — Layer definitions, generic-to-IHP mapping, SPICE models
> - [ihp130_grules.py](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/ihp130_mapped/ihp130_grules.py) — All design rules (min width, spacing, enclosure, etc.)
> - [mappedpdk.py](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/mappedpdk.py) — Base [MappedPDK](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/mappedpdk.py#236-1118) class defining the valid generic layers

---
---

## 0. Important Layers update
+ Pcells have a Substrate_Layer that glayout doesn't. Without this ptap or ntap is not recognised
+ nSD layer triggers errors by not recognizing the transistors
+ Pwell Layer doesn't exist. Trigger errors.
+ There is a layer called 'nBuLay.drawing which comes with Pcells but doesn't appear
+ There is a heat transfer layer that needs to be deleted

## 1. GDS Layer Table

The IHP 130nm layers are mapped to GDS layer/datatype pairs:

| Layer Name | GDS (Layer, Datatype) | Purpose |
|---|---|---|
| `activ` | (1, 0) | Active / diffusion area |
| `gatpoly` | (5, 0) | Polysilicon gate |
| `nsd` | (7, 0) | N+ source/drain implant |
| `psd` | (14, 0) | P+ source/drain implant |
| `nwell` | (31, 0) | N-well |
| `pwell` | (46, 0) | P-well |
| `cont` | (6, 0) | Contact (diffusion/poly to metal1) |
| `metal1` | (8, 0) | Metal 1 |
| `via1` | (19, 0) | Via 1 (metal1 → metal2) |
| `metal2` | (10, 0) | Metal 2 |
| `via2` | (29, 0) | Via 2 (metal2 → metal3) |
| `metal3` | (30, 0) | Metal 3 |
| `via3` | (49, 0) | Via 3 (metal3 → metal4) |
| `metal4` | (50, 0) | Metal 4 |
| `via4` | (66, 0) | Via 4 (metal4 → metal5) |
| `metal5` | (67, 0) | Metal 5 (top metal) |
| `mim` | (36, 0) | MIM capacitor plate |

Pin and label layers follow the convention [(layer, 2)](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/mappedpdk.py#316-411) for pins and [(layer, 25)](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/mappedpdk.py#316-411) for labels.

---

## 2. Generic-to-IHP Layer Mapping

The framework uses **generic layer names** (glayers) internally. These are mapped to IHP-specific names:

| Generic Name | IHP Layer | Description |
|---|---|---|
| `met1`–`met5` | `metal1`–`metal5` | Metal routing layers |
| `via1`–`via4` | `via1`–`via4` | Inter-metal vias |
| `mcon` | `cont` | Contact to metal1 |
| `active_diff` | `activ` | FET diffusion |
| `active_tap` | `activ` | Well tap (same physical layer) |
| `poly` | `gatpoly` | Gate poly |
| `n+s/d` | `nsd` | N-type source/drain implant |
| `p+s/d` | `psd` | P-type source/drain implant |
| `nwell` | `nwell` | N-well |
| `pwell` | `pwell` | P-well |
| `capmet` | `mim` | MIM capacitor |

---

## 3. SPICE Device Models

| Device | Model Name |
|---|---|
| NMOS FET | `sg13_lv_nmos` |
| PMOS FET | `sg13_lv_pmos` |
| MIM Capacitor | `cap_cmim` |

---

## 4. Design Rules (from [ihp130_grules.py](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/ihp130_mapped/ihp130_grules.py))

All dimensions are in **micrometers (µm)**.

### 4.1 Well Rules

| Rule | Value (µm) |
|---|---|
| `nwell` min width | 0.86 |
| `nwell` min separation | 1.27 |
| `nwell` → `active_tap` enclosure | 0.18 |
| `pwell` → `active_tap` enclosure | 0.18 |
| `dnwell` min width | 3.0 |
| `dnwell` min separation | 6.3 |
| `dnwell` → `nwell` separation | 4.5 |

### 4.2 Diffusion & Implant Rules

| Rule | Value (µm) |
|---|---|
| `active_diff` min width | 0.15 |
| `active_diff` min separation | 0.21 |
| `active_tap` min width | 0.15 |
| `active_tap` min separation | 0.21 |
| `n+s/d` min width | 0.38 |
| `n+s/d` min separation | 0.38 |
| `p+s/d` min width | 0.38 |
| `p+s/d` min separation | 0.38 |
| `n+s/d` / `p+s/d` → `active_diff` enclosure | 0.13 |
| `n+s/d` / `p+s/d` → `active_tap` enclosure | 0.13 |

### 4.3 Poly Rules

| Rule | Value (µm) |
|---|---|
| `poly` min width | 0.13 |
| `poly` min separation | 0.18 |
| `poly` extension (beyond active) | 0.13 |
| `active_diff` overhang by `poly` | 0.25 |
| `active_diff` → `poly` min separation | 0.07 |
| `poly` → `mcon` enclosure | 0.0 |
| `poly` → `mcon` separation | 0.06 |

### 4.4 Contact (mcon) Rules

| Rule | Value (µm) |
|---|---|
| `mcon` width (fixed) | 0.16 |
| `mcon` min separation | 0.18 |
| `active_diff` → `mcon` enclosure | 0.0 |
| `active_tap` → `mcon` enclosure | 0.0 |
| `mcon` → `met1` enclosure | 0.0 |

### 4.5 Metal & Via Stack Rules

| Layer | Min Width (µm) | Min Separation (µm) | Fixed Via Width (µm) |
|---|---|---|---|
| **met1** | 0.16 | 0.18 | — |
| **via1** | 0.19 | 0.22 | 0.19 |
| **met2** | 0.20 | 0.21 | — |
| **via2** | 0.19 | 0.22 | 0.19 |
| **met3** | 0.20 | 0.21 | — |
| **via3** | 0.19 | 0.22 | 0.19 |
| **met4** | 0.20 | 0.21 | — |
| **via4** | — | 0.22 | 0.19 |
| **met5** | 0.20 | 0.21 | — |

**Enclosure rules** (via to enclosing metal) are all set to `0.0 µm` in this mapping.

### 4.6 MIM Capacitor Rules

| Rule | Value |
|---|---|
| `capmet` min separation | 1.2 µm |
| `met4` → `capmet` enclosure | 0.14 µm |
| `capmettop` layer | (71, 20) |
| `capmetbottom` layer | (70, 20) |

---

## 5. How These Rules Are Used in the Transmission Gate

The [transmission_gate_with_inv.py](file:///home/sapta/eda/designs/hh/gLayout-IHP130/blocks/composite/sapta/transmission_gate_with_inv.py) layout uses these PDK rules in several ways:

1. **`pdk.activate()`** — Sets IHP130 as the active PDK so all generators use the correct rules
2. **`nmos()` / `pmos()`** — Creates NMOS/PMOS FETs using `sg13_lv_nmos` / `sg13_lv_pmos` models, with `width`, `length`, `fingers`, `multipliers` parameters. The generators internally apply poly, diffusion, contact, and implant rules
3. **`via_stack(pdk, "met2", "met3")`** — Builds via stacks between metal layers using the via width (0.19 µm), separation (0.22 µm), and metal enclosure rules
4. **`pdk.util_max_metal_seperation()`** — Queries the maximum metal separation across the stack to determine safe placement spacing
5. **Routing** — `c_route`, `L_route`, and `straight_route` use met1/met2/met3 width and separation rules for DRC-clean routing
6. **Labels & Pins** — Use `pdk.get_glayer("met2_pin")` and `pdk.get_glayer("met2_label")` to place pin rectangles and text on the correct GDS layers

> [!IMPORTANT]
> Several enclosure rules are set to `0.0 µm` in this mapping (e.g., `mcon` → `met1`, via → metal). This is a simplification; the actual IHP DRC may enforce non-zero enclosures. The project includes a KLayout DRC rule deck ([ihp130_drc.lydrc](file:///home/sapta/eda/designs/hh/gLayout-IHP130/src/glayout/pdk/ihp130_mapped/ihp130_drc.lydrc)) for full design rule checking.

---

## 6. GDS Write Settings

| Setting | Value |
|---|---|
| Precision | 1 nm (`1e-9`) |
| Cell cache | Disabled |
