# Missing BRDF/PBR Papers Analysis

This document identifies influential BRDF/PBR papers from the papi database that are NOT yet referenced in `brdf_and_shading_effects.md`.

## Executive Summary

Updated 2026-05-21: all explicit arXiv IDs referenced in this repo's tracked docs now exist in the local `papi`
database. The coverage pass also added project-used SfM/matching papers and public-PDF entries for several classic
BRDF/PBR references.

Remaining gaps are mostly non-arXiv classics or resources that are books, course pages, tutorials, or datasets rather
than normal paper entries. Those need manual source selection before ingestion.

## Papers Already Referenced in the Document

### Neural Rendering (NeRF/SDF-based)
- NeRF (Mildenhall et al.)
- Mip-NeRF (Barron et al.)
- Ref-NeRF (Verbin et al.)
- NeRD (Boss et al.)
- NeRFactor (Zhang et al.)
- NeRV (Srinivasan et al.)
- NeuS (Wang et al.)
- VolSDF (Yariv et al.)
- NeRFW/NeRF in the Wild (Martin-Brualla et al.)
- NeRFReN (Guo et al.)

### Classic BRDF/PBR
- PBRT book (Pharr, Jakob, Humphreys)
- Oren-Nayar (Generalization of Lambert's Reflectance Model)
- Torrance-Sparrow (Theory for Off-Specular Reflection)
- Disney BRDF (Burley - Physically-Based Shading at Disney)
- Disney BSDF (Burley - Extending the Disney BRDF to a BSDF with Integrated Subsurface Scattering)
- Heitz (Understanding Masking-Shadowing, Microfacet surveys)
- Walter et al. (Microfacet Models for Refraction through Rough Surfaces)
- Schlick (Inexpensive BRDF Model for Physically-based Rendering)
- Karis (Real Shading in Unreal Engine 4)
- Ramamoorthi-Hanrahan (Efficient Representation for Irradiance Environment Maps)
- Debevec (Rendering Synthetic Objects into Real Scenes)
- Jensen et al. (Practical Model for Subsurface Light Transport)

## Key Papers Found in Database NOT Yet Referenced

### 1. Tensor-Based Inverse Rendering
**TensoRF** (Chen et al., 2022)
- **Contribution**: Tensorial radiance fields using CP/VM decomposition
- **Relevance**: Foundation for TensoIR; efficient tensor factorization for radiance fields
- **Citation**: Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su. TensoRF: tensorial radiance fields. ECCV 2022.

**TensoIR** (Jin et al., 2023)
- **Contribution**: Tensor factorization-based inverse rendering; jointly estimates geometry, materials, and illumination
- **Relevance**: State-of-the-art inverse rendering with accurate secondary shading effects (shadows, indirect lighting)
- **Citation**: Haian Jin, Isabella Liu, Peijia Xu, Xiaoshuai Zhang, Songfang Han, Sai Bi, Xiaowei Zhou, Zexiang Xu, and Hao Su. TensoIR: Tensorial Inverse Rendering. CVPR 2023.

### 2. Neural Incident Light Field Methods
**NeILF** (Yao et al., 2022)
- **Contribution**: Neural Incident Light Field for physically-based material estimation; fully 5D light field representation
- **Relevance**: Handles occlusions and indirect lights naturally without multiple ray tracing bounces
- **Citation**: Yao Yao, Jingyang Zhang, Jingbo Liu, Yihang Qu, Tian Fang, David McKinnon, Yanghai Tsin, and Long Quan. NeILF: Neural Incident Light Field for Physically-based Material Estimation. ECCV 2022.

**NeILF++** (mentioned in PBR-NeRF)
- **Contribution**: Extends NeILF with inter-reflectable light fields; combines NeILF + BRDF fields + SDF for geometry
- **Relevance**: State-of-the-art material estimation before PBR-NeRF
- **Note**: Full citation needs verification from database

### 3. Physics-Based Neural Rendering
**PBR-NeRF** (Wu et al., 2025)
- **Contribution**: Inverse rendering with physics-based neural fields; introduces energy conservation loss and NDF-weighted specular loss
- **Relevance**: Addresses "baked-in" specular highlights issue; enforces physical validity in BRDFs
- **Citation**: Sean Wu, Shamik Basu, Tim Brödermann, Luc Van Gool, and Christos Sakaridis. PBR-NeRF: Inverse Rendering with Physics-Based Neural Fields. arXiv 2025.

**Neural-PBIR** (Sun et al., 2023)
- **Contribution**: Combines neural reconstruction with physics-based inverse rendering; neural material and lighting distillation
- **Relevance**: Accurate and efficient object reconstruction pipeline
- **Citation**: Cheng Sun, Guangyan Cai, Zhengqin Li, Kai Yan, Cheng Zhang, Carl Marshall, Jia-Bin Huang, Shuang Zhao, and Zhao Dong. Neural-PBIR Reconstruction of Shape, Material, and Illumination. ICCV 2023.

### 4. Advanced Inverse Rendering Methods
**NEFII** (Wu et al., 2023)
- **Contribution**: Near-field indirect illumination; Monte Carlo sampling based path tracing for inverse rendering
- **Relevance**: Models sharp inter-reflections and recovers accurate roughness/albedo
- **Citation**: Haoqian Wu, Zhipeng Hu, Lincheng Li, Yongqiang Zhang, Changjie Fan, and Xin Yu. NEFII: Inverse Rendering for Reflectance Decomposition with Near-field Indirect Illumination. CVPR 2023.

**SIRE-IR** (Yang et al., 2023)
- **Contribution**: Inverse rendering for BRDF reconstruction with shadow and illumination removal in high-illuminance scenes
- **Relevance**: Handles strong shadows and indirect illumination; masked visibility network approach
- **Citation**: Ziyi Yang. SIRE-IR: Inverse Rendering for BRDF Reconstruction with Shadow and Illumination Removal in High-illuminance Scenes. arXiv 2023.

**ENVIDR** (Liang et al., 2023)
- **Contribution**: Implicit differentiable renderer with neural environment lighting
- **Relevance**: Decouples environment light from directional MLP; enables scene relighting
- **Citation**: Ruofan Liang, Hongzhi Sun, Nandita Vijaykumar. ENVIDR: Implicit Differentiable Renderer with Neural Environment Lighting. arXiv 2023.

**IRON** (Zhang et al., 2022)
- **Contribution**: Inverse rendering by optimizing neural SDFs and materials from photometric images
- **Relevance**: Joint optimization of geometry and materials
- **Citation**: Kai Zhang, Fujun Luan, Zhengqi Li, and Noah Snavely. IRON: Inverse Rendering by Optimizing Neural SDFs and Materials from Photometric Images. CVPR 2022.

### 5. Other Notable Methods
**PhySG** (Zhang et al., 2021)
- **Contribution**: Inverse rendering with spherical Gaussians for physics-based material editing and relighting
- **Relevance**: Uses Spherical Gaussians to model environment lighting; influential for many subsequent works
- **Citation**: Kai Zhang, Fujun Luan, Qianqian Wang, Kavita Bala, and Noah Snavely. PhySG: Inverse Rendering with Spherical Gaussians for Physics-based Material Editing and Relighting. CVPR 2021.

**Neural Reflectance Fields** (Bi et al., 2020)
- **Contribution**: Deep reflectance volumes for relightable reconstructions from multi-view photometric images
- **Relevance**: Early work on neural reflectance acquisition
- **Citation**: Sai Bi, Zexiang Xu, Pratul Srinivasan, Ben Mildenhall, Kalyan Sunkavalli, Miloš Hašan, Yannick Hold-Geoffroy, David Kriegman, and Ravi Ramamoorthi. Neural Reflectance Fields for Appearance Acquisition. arXiv 2020.

## Current Coverage Added for mini-mesh

### Neural rendering and Gaussian splatting
- **nerfren** (`2111.15234`) - NeRFReN: Neural Radiance Fields with Reflections
- **nerv** (`2012.03927`) - NeRV: Neural Reflectance and Visibility Fields for Relighting and View Synthesis
- **nrvf** (`2008.03824`) - Neural Reflectance Fields for Appearance Acquisition
- **gcmc** (`2404.09591`) - 3D Gaussian Splatting as Markov Chain Monte Carlo

### SfM and feature matching dependencies
- **colmap-sfm** - Structure-from-Motion Revisited
- **superpoint** (`1712.07629`) - SuperPoint: Self-Supervised Interest Point Detection and Description
- **superglue** (`1911.11763`) - SuperGlue: Learning Feature Matching with Graph Neural Networks
- **lightglue** (`2306.13643`) - LightGlue: Local Feature Matching at Light Speed
- **vg-sfm** (`2312.04563`) - Visual Geometry Grounded Deep Structure From Motion
- **hf-net** (`1812.03506`) - From Coarse to Fine: Robust Hierarchical Localization at Large Scale

### Classic/public-PDF BRDF and rendering references
- **oren-nayar** - Generalization of Lambert's Reflectance Model
- **nicodemus-reflectance** - Geometrical Considerations and Nomenclature for Reflectance
- **debevec-ibl** - Rendering Synthetic Objects into Real Scenes
- **subsurface-light-transport** - A Practical Model for Subsurface Light Transport
- **microfacet-survey** - A Survey of Microfacet Models for Rough Surfaces
- **disney-bsdf** - Extending the Disney BRDF to a BSDF with Integrated Subsurface Scattering

## Remaining Gaps in the Database

The following named references still need manual source selection or are not normal paper entries:

### Missing or unresolved classic papers/resources
- **PBRT book** - book/online reference, not a paper entry
- **Torrance-Sparrow** - Theory for Off-Specular Reflection
- **Schlick** - An Inexpensive BRDF Model for Physically-based Rendering
- **Kajiya and Von Herzen** - Ray Tracing Volume Densities
- **NeILF++** - mentioned in PBR-NeRF context; full citation still needs verification
- **Phong (1975)** - Original specular reflection model
- **Blinn (1977)** - Modified specular model
- **Lambert** - Original diffuse reflectance work
- **Ward (1992)** - Anisotropic BRDF model
- **Ashikhmin-Shirley (2000)** - Anisotropic Phong BRDF
- **He et al. (1991)** - Comprehensive physical BRDF model

### Missing Measured BRDF Datasets
- **MERL BRDF Database** (100 materials) - Mentioned extensively in papers but original database papers not in index

## Recommendations for Document Enhancement

### High Priority Additions
1. **TensoIR** - State-of-the-art tensor-based inverse rendering
2. **NeILF/NeILF++** - Neural incident light field framework
3. **PBR-NeRF** - Latest physics-based approach with energy conservation
4. **PhySG** - Influential spherical Gaussian lighting method

### Medium Priority Additions
5. **NEFII** - Near-field indirect illumination
6. **TensoRF** - Foundation for tensor-based approaches
7. **Neural-PBIR** - Efficient hybrid neural-physics pipeline
8. **IRON** - SDF-based inverse rendering

### Nice-to-Have Additions
9. **SIRE-IR** - High-illuminance scene handling
10. **ENVIDR** - Neural environment lighting
11. **Neural Reflectance Fields** (Bi et al.) - Early neural reflectance work

## Suggested New Section for Document

Consider adding a new section:

### Section: Tensor-Based Representations for Neural Rendering
- Describe how tensor factorization (CP, VM decomposition) improves efficiency
- TensoRF for radiance field reconstruction
- TensoIR for inverse rendering with secondary effects

### Section Enhancement: Neural Incident Light Fields
- Expand NeILF discussion (currently missing)
- Connection to NeILF++
- Relationship to environment map representations

## Database Characteristics

After the 2026-05-21 update, `papi` covers the repo's explicit arXiv references and the main public-PDF BRDF/PBR
references used by the docs. It is still stronger on neural rendering and inverse rendering than on older graphics
literature, because several classic references need manual PDF/DOI handling.

---

## Papers Added from arXiv (2025-01-15)

### Survey and Review Papers
- **mitsuba-2** (2504.01402) - A Survey on Physics-based Differentiable Rendering
  - Comprehensive theoretical framework for computing unbiased gradients of rendering equation
  - Covers both explicit boundary sampling and reparameterization approaches
  - Categories: path-space differentiable rendering, warped-area sampling, implicit surfaces

- **survey** (2005.12518) - Survey: Machine Learning in Production Rendering
  - Covers deep neural networks in production rendering contexts
  - Topics: denoising, light transport, path guiding

### Neural BRDF Representations
- **neural-brdfs** (2111.03797) - Neural BRDFs: Representation and Operations
  - Introduces "Neural BRDF Algebra" for compressing BRDFs into latent vectors
  - Operations in latent space: layering, interpolation, sampling
  - Evaluation: 5ms for 1920×1080 buffer using NVIDIA CUTLASS

- **on-neural-brdfs** (2502.15480) - On Neural BRDFs: A Thorough Comparison of State-of-the-Art Approaches
  - Comprehensive evaluation of neural BRDF approaches
  - Novel additive combination strategy for diffuse/specular parts
  - Input mapping that ensures reciprocity exactly by construction

- **neural-brdf** (2102.05963) - Neural BRDF Representation and Importance Sampling
  - Appearance modeling using neural networks
  - Importance sampling for efficient rendering

- **pbnbrdf** (2411.02347) - Physically Based Neural Bidirectional Reflectance Distribution Function
  - Physically based neural approach to BRDF modeling
  - Material reconstruction using neural fields

- **nbrdf-is** (2505.08998) - Neural BRDF Importance Sampling by Reparameterization
  - Generative models for BRDF importance sampling
  - Reparameterization techniques

- **inv-brdf** (2008.04030) - Invertible Neural BRDF for Object Inverse Rendering
  - Bayesian inference using normalizing flows
  - Invertible neural networks for inverse rendering

### BRDF Technical Papers
- **is-brdf** (2304.04088) - Importance Sampling BRDF Derivatives
  - Differentiable rendering context
  - BRDF derivative sampling for gradient computation

- **eon** (2410.18026) - EON: A Practical Energy-preserving Rough Diffuse BRDF
  - Energy-preserving rough diffuse BRDF model
  - Practical importance sampling approach

- **deep-brdf-sampling** (2210.03510) - Learning to Learn and Sample BRDFs
  - Active sampling and meta-learning for BRDF acquisition
  - Meta-learning approach for BRDF sampling

## Important Finding: Classic BRDF Papers NOT on arXiv

**The classic BRDF papers listed below are NOT on arXiv because they predate arXiv's launch in 1991.** These foundational papers are only available as:
- Original publications (ACM/SIGGRAPH/IEEE)
- Scanned PDFs from archival sources
- Citations within modern papers

### Classic Papers with NO arXiv Version
- **Phong (1975)** - Original specular reflection model - Pre-dates arXiv
- **Blinn (1977)** - Modified specular model - Pre-dates arXiv
- **Lambert** - Original diffuse reflectance work - Pre-dates arXiv (18th century work!)
- **Cook-Torrance (1982)** - Seminal microfacet BRDF model - Pre-dates arXiv
- **Ward (1992)** - Anisotropic BRDF model - Pre-dates arXiv
- **Ashikhmin-Shirley (2000)** - Anisotropic Phong BRDF - May be available (post-arXiv)
- **He et al. (1991)** - Comprehensive physical BRDF model - Pre-dates arXiv
- **Kajiya (1986)** - The Rendering Equation - Pre-dates arXiv
- **Nicodemus et al.** - Geometrical Considerations and Nomenclature for Reflectance - Pre-dates arXiv

### Potential Sources for Classic Papers
- ACM Digital Library
- IEEE Xplore
- Graphics Gems series books
- Course readers/surveys that cite these works
- Modern survey papers that review historical BRDF models

## Summary

The January 2025 pass added **11 papers** to the papi database:
- 2 survey/review papers on differentiable rendering and machine learning in production
- 7 neural BRDF representation papers covering algebra, comparison, importance sampling, and invertible methods
- 2 technical BRDF papers on derivatives and energy preservation

The May 2026 pass closed the repo-visible arXiv gaps and added public-PDF entries for the most directly cited classic
references. Remaining gaps are manual-source classics, books, tutorials, or datasets rather than missing arXiv papers.
