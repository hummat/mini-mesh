# BRDF and Shading Effects Cheat Sheet

This document summarizes the main shading / BRDF effects we discussed and how they relate to SDFStudio-style configs
(`--pipeline.model.sdf-field.*`). It also lists representative papers for deeper reading, especially works that try to
explicitly model some of these effects in neural fields.

**See also**: [`pbr_learning_starter_pack.md`](pbr_learning_starter_pack.md) — curated video/reading list for learning PBR extraction

---

## 1. Core Shading and BRDF Concepts

- **BRDF (Bidirectional Reflectance Distribution Function)**  
  Describes how light is reflected at a surface as a function of incident and outgoing directions. A BRDF encodes the
  “material” independent of lighting and geometry.

  - Classic intros:  
    - Pharr, Jakob, Humphreys – *Physically Based Rendering (PBRT)*, 3rd ed.  
    - Nicodemus et al. – *Geometrical Considerations and Nomenclature for Reflectance*.

- **Diffuse reflection / Lambertian shading**  
  Ideal matte reflection; outgoing radiance is independent of view direction, proportional to `max(0, n·l)`.

  - Oren, Nayar – *Generalization of Lambert's Reflectance Model* (Oren–Nayar BRDF).

- **Specular reflection / highlights**  
  Mirror-like component concentrated near the reflection direction; responsible for shiny highlights.

  - Early microfacet: Torrance, Sparrow – *Theory for Off-Specular Reflection*.  
  - Practical game/PBR overview: Karis – *Real Shading in Unreal Engine 4*.

- **Diffuse vs specular separation (albedo vs highlights)**  
  Modeling color as a sum of a view-independent “albedo” term and a view-dependent specular term.

  - NeRFactor: Zhang et al. – *NeRFactor: Neural Factorization of Shape and Reflectance under Unknown Illumination*.  
  - Neural Reflectance Fields: Bi et al. – *Deep Reflectance Volumes* / related NeRF-based reflectance works.

- **Specular tint / metallic vs dielectric behavior**  
  Colored specular (metals) vs nearly white specular (dielectrics); in PBR often controlled by a metallic factor and
  F₀ (base reflectivity).

  - Burley – *Physically-Based Shading at Disney*.  
  - Burley – *Extending the Disney BRDF to a BSDF with Integrated Subsurface Scattering*.

- **Roughness**  
  Parameter controlling microfacet orientation distribution. Low roughness → sharp highlights; high roughness → wide,
  blurred highlights.

  - Heitz – *Understanding the Masking-Shadowing Function in Microfacet-Based BRDFs*.  
  - Heitz – *A Survey of Microfacet Models for Rough Surfaces*.

- **Microfacet BRDF models (GGX, Beckmann, etc.)**  
  Physically-based specular models using a normal distribution function (NDF), masking–shadowing, and Fresnel.

  - Walter et al. – *Microfacet Models for Refraction through Rough Surfaces*.  
  - PBRT book again for detailed derivations.

- **Masking–shadowing (geometry term)**  
  Microfacets self-occlude each other, reducing visible specular energy especially at grazing angles.

- **Energy conservation & reciprocity**  
  Physical constraints on BRDFs: total reflected energy ≤ incoming, and swapping light/view directions leaves the BRDF
  unchanged.

---

## 2. Angular / View-Dependent Effects

- **Angle of incidence / `n·v` term**  
  Cosine of the angle between surface normal and view direction; used in shading, foreshortening, Fresnel, and
  orientation losses.

- **Foreshortening**  
  Apparent shrinking / darkening of surfaces as they tilt away from the viewer; mathematically tied to cosines like
  `n·v` or `n·l`.

- **Limb darkening**  
  Generic term for surfaces or objects appearing darker near silhouettes (grazing angles), due to angular effects and
  transport.

- **Fresnel effect**  
  Reflectance increasing at grazing angles; often approximated in graphics by Schlick’s formula.

  - Schlick – *An Inexpensive BRDF Model for Physically-based Rendering*.  
  - Also discussed extensively in PBRT and Disney/UE4 shading notes.

- **View-dependent appearance / view-dependent radiance**  
  Color changes with view direction even for fixed illumination, encompassing specular, Fresnel, anisotropy, etc.

  - Mildenhall et al. – *NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis*.  
  - Barron et al. – *Mip-NeRF* and *Mip-NeRF 360* (better anti-aliasing and unbounded scenes).

---

## 3. Reflection, Refraction, Environment

- **Reflection law (mirror reflection direction)**  
  Outgoing direction `r = v - 2 (n·v) n`; governs where specular highlights and mirror reflections appear.

- **Environment reflections / environment mapping**  
  Reflective objects showing the surrounding scene; often modeled with environment maps or image-based lighting.

  - Ramamoorthi, Hanrahan – *An Efficient Representation for Irradiance Environment Maps*.  
  - Debevec – *Rendering Synthetic Objects into Real Scenes* (light probes).

- **Refraction / transmission**  
  Light bending when passing between media (Snell’s law), plus internal transmission.

  - Walter et al. – *Microfacet Models for Refraction through Rough Surfaces*.  
  - Neural fields with refraction: e.g. Guo et al. – *NeRFReN: Neural Radiance Fields with Reflections and Refractions*.

- **Transparent / refractive objects**  
  Glass, water, etc. require modeling multiple interfaces, refraction, and internal reflections. Standard NeRF/SDF
  pipelines (including SDFStudio/mini-mesh) largely treat these as “out of scope”.

- **Subsurface scattering**  
  Light entering a translucent medium, scattering internally, and exiting at nearby points (skin, wax, marble).

  - Jensen et al. – *A Practical Model for Subsurface Light Transport*.  
  - RenderMan/Disney subsurface models in Burley’s work.

- **Volumetric light transport**  
  Light absorption, scattering, and emission in participating media (fog, smoke, semi-transparent volumes). NeRF’s
  volumetric rendering is a simplified version of this.

  - Kajiya, Von Herzen – *Ray Tracing Volume Densities*.  
  - NeRF again for the simplified volumetric rendering integral.

---

## 4. NeRF / SDF-Specific Modeling Topics

- **SDF normals (`∇SDF`) and geometric gradients**  
  Deriving surface normals from the gradient of a signed distance function; used heavily in NeuS/SDFStudio.

  - Wang et al. – *NeuS: Learning Neural Implicit Surfaces by Volume Rendering for Multi-view Reconstruction*.  
  - Yariv et al. – *VolSDF: Volume Rendering of Signed Distance Functions*.

- **View-direction encoding vs reflection-direction encoding**  
  Feeding the color network either encoded view directions or encoded reflection directions (or both).

  - Mildenhall et al. – *NeRF* (view-direction encoding).  
  - Verbin et al. – *Ref-NeRF: Structured View-Dependent Appearance for Neural Radiance Fields* (reflection dirs,
    diffuse/specular split, tint, `n·v`).

- **Diffuse/specular decomposition in neural fields (Ref-NeRF-style)**  
  Architectures that explicitly separate diffuse and specular components to stabilize geometry + appearance learning.

  - Verbin et al. – *Ref-NeRF*.  
  - Boss et al. – *NeRD: Neural Reflectance Decomposition from Image Collections*.  
  - Zhang et al. – *NeRFactor* (factorization of shape, reflectance, and lighting).

- **Learned roughness and material parameters in NeRF-like models**  
  Predicting roughness, metallic, or other material parameters inside a neural field and using them in a BRDF head.

  - Srinivasan et al. – *NeRV: Neural Reflectance and Visibility Fields for Relighting and View Synthesis*.  
  - Boss et al. – *NeRD*; Hasselgren et al. – *Neural Reflectance Fields*.  
  - Recent “neural PBR” works that combine NeRF with explicit microfacet BRDFs.

- **Lighting / environment estimation in neural fields**  
  Some methods explicitly estimate lighting (environment maps or spherical harmonics) jointly with geometry and
  reflectance.

  - Martin-Brualla et al. – *NeRF in the Wild* (NeRFW).  
  - Srinivasan et al. – *NeRV*.  
  - Boss et al. – *NeRD*.

---

## 5. How This Relates to SDFStudio Flags

In SDFStudio/mini-mesh, the following SDF field flags are loosely inspired by Ref-NeRF and related works:

- `use_diffuse_color`  
  Approximates a diffuse/specular decomposition: diffuse color predicted from geometry features; specular learned in
  the view-dependent MLP. Conceptually similar to Ref-NeRF’s “diffuse color” head.

- `use_specular_tint`  
  Adds a learned RGB tint to the specular component, analogous to metallic/colored specular behavior in Disney/UE4
  shading and Ref-NeRF’s specular tint.

- `use_reflections`  
  Uses reflection directions as part of the view encoding, following Ref-NeRF’s reflection-direction encoding. This
  strongly couples specular highlight position to geometry and normals.

- `use_n_dot_v`  
  Supplies `n·v` directly to the color MLP, making Fresnel-like ramps and limb-darkening behavior much easier to learn.
  Ref-NeRF also uses such angular cues.

- `enable_pred_roughness` (with `use_reflections=True`)  
  Predicts a roughness in `[0, 1]` and uses it to mix view-direction and reflection-direction encodings. This is a very
  lightweight proxy for roughness-dependent specular behavior; it is **not** a full analytic microfacet BRDF, but
  nudges the network toward roughness-consistent highlights and provides an interpretable roughness map.

These flags give you Ref-NeRF–style signals and biases inside an SDF-based model, but the underlying rendering is still
fully learned by an MLP — there is no explicit microfacet BRDF, env lighting, or guaranteed physical correctness.

