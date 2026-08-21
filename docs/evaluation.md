# Evaluating splat quality

`ns-eval` reports PSNR, SSIM and LPIPS on held-out views. Every tuning decision
this pipeline makes has been justified with those three numbers. Four subjective
studies published between 2024 and 2025 measured how well those numbers track
what people see in a Gaussian splat, and the answer is: not well enough
to settle a close call.

This document collects the evidence, says which of our decisions it invalidates,
and proposes what to measure instead.

## What the studies found

Each study collected Mean Opinion Scores from human viewers on a set of
deliberately degraded splats, then asked how well each objective metric
reproduced the human ranking. Numbers below are Spearman rank correlation with
MOS. Higher is better; 1.0 would mean the metric orders stimuli exactly as
people do.

| Metric | 3DGS-VBench | MUGSQA (main) | 3DGS-QA |
|---|---|---|---|
| PSNR | 0.50 | 0.52 | not reported |
| SSIM | 0.51 | 0.37 | 0.31 |
| MS-SSIM | 0.50 | 0.64 | not reported |
| LPIPS | 0.51 | 0.41 (VGG) / 0.44 (Alex) | 0.34 |
| FSIM | 0.59 | 0.68 | not reported |
| IW-SSIM | 0.63 | not reported | not reported |
| CW-SSIM | not reported | 0.74 | not reported |
| DISTS | 0.73 | not reported | not reported |
| BRISQUE | 0.24 | not reported | 0.33 |
| DOVER | **0.94** | not reported | not reported |
| VSFA | **0.94** | not reported | not reported |
| FAST-VQA | **0.93** | not reported | 0.29 |
| DBCNN (fine-tuned) | not reported | **0.88** | not reported |
| GSOQA (fine-tuned) | not reported | not reported | **0.77** |

The three studies disagree on plenty, and they degrade splats in different ways.
They agree on the part that matters here: PSNR, SSIM and LPIPS all land near 0.5
or below, and none of the three separates itself from the other two.

The papers also report Kendall correlation, which converts to something more
concrete. Ignoring ties, a metric with Kendall tau of t ranks a random pair of
stimuli the way the averaged panel ranked them about (1+t)/2 of the time. On
3DGS-VBench that puts PSNR at 68%, LPIPS at 68% and DISTS at 76%. On 3DGS-QA,
LPIPS drops to 64%. A coin flip is 50%.

Read that as agreement with a mean opinion score, not with any individual
viewer. Per-viewer agreement is lower, since the panel average smooths out
disagreement between people, and none of these papers reports the subject-level
numbers that would pin it down. Either way, a metric that reproduces the panel's
ordering two times in three is not settling a close call.

### What each study degraded

The studies are not interchangeable, and the differences decide which of our
questions they can answer.

**3DGS-VBench** ([2508.07038](https://arxiv.org/abs/2508.07038)) is the one aimed
at delivery. 660 compressed models, 11 scenes, six compression methods at
several parameter levels each, 50 participants scoring rendered videos. This is
the closest published analogue to our own container and pruning decisions.

**MUGSQA** ([2511.06830](https://arxiv.org/abs/2511.06830)) varies the input
instead: view count (72/36/9), resolution (1080/720/480 square), camera distance
(5 m/2 m/1 m) and point cloud initialisation quality. 1,970 samples from 55
Sketchfab meshes rendered in Blender with exact poses in NeRF-synthetic format.
This is the synthetic ground-truth benchmark we sketched out for ourselves. It
exists, and the code and data are released.

**3DGS-QA** ([2511.08032](https://arxiv.org/abs/2511.08032)) degrades the
exported asset directly: primitive count reduced to 75/50/25%, positional noise,
spherical harmonic perturbation, plus reduced views and truncated training.
225 models across 15 object types. Its downsampling axis is the nearest thing
in the literature to our cleanup script, with one difference that matters (see
below).

**GS-QA** ([2502.13196](https://arxiv.org/abs/2502.13196)) is the dissenting
result: correlations above 0.8 for 360-degree scenes, with FSIM and MS-SSIM on
top and ST-LPIPS best on forward-facing scenes. The dissent is explainable. Its
64 stimuli come from eight scenes crossed with seven GS methods plus
Mip-NeRF 360, so the quality range is wide and the comparisons are coarse.
Ranking Scaffold-GS against LightGaussian is not the same problem as ranking two
parameter settings of one method, and the coarse comparison is the one the
metrics handle.

## What this invalidates

**The cap_max sweep.** We measured 100k/250k/500k/1M Gaussians on
`gaudi_fountain` and found PSNR and SSIM blind to the whole range while LPIPS
moved from 0.451 to 0.282. We read that as LPIPS being the sensitive metric.
The correlation numbers say something weaker: LPIPS moved, and we do not know
how much of that motion a viewer would notice. The file size went from 23.8 MB
to 232.9 MB over the same range, so the decision has a real cost on one side and
an unverified benefit on the other.

**The cleanup threshold.** Filtering at opacity 0.05 removes between 4.9% and
62% of the Gaussians depending on the scene, and it is not free. Paired testing
puts the cost at 0.0007 LPIPS on `gaudi_fountain` and 0.0059 on `r2d2_new`, the
same sign on every frame of both, with PSNR and SSIM agreeing. It was called
free because the marginal spread is 0.05 and 0.035, which buried it. The cost is
small enough that a median 28% size saving is still worth paying, but "free" was
the wrong word and it was reached the wrong way.

3DGS-QA measured content-blind random pruning at 25/50/75% and found it degrades
MOS smoothly. Our filter is attribute-based, targeting Gaussians the model
itself marked nearly transparent, which should cost less than random pruning at
the same rate. Nobody has measured that, and the 62% scenes remain the ones to
worry about.

**The container choice.** SPZ against SOG is a quantisation decision applied to
a fixed set of Gaussians. GS-QA evaluates SOG, but as a reconstruction *method*
with spherical harmonics removed during training, not as a container applied
afterwards. Nothing published covers our version of the question.

**The frame-count experiment.** Invalid, and not for a subtle reason. The design
held a fixed set of 11 source frames out of every configuration so the two runs
would be scored on the same ground truth. It did not survive contact with
`ceil`. The split fraction has to be `(N-E)/N` exactly; the script validated
that at full precision and then passed a six-decimal rounding to training, and
`0.905983 * 117` is `106.00001`, so `ceil` returned 107 instead of 106. Both
configurations held out 10 frames instead of 11, at different positions, and the
two runs share exactly one ground-truth image out of ten. The reported tie
compared different pictures.

The fix is to stop deriving the split from a float. Name the files so
`eval_mode=filename` selects them, which cannot drift. Retraining is cheap
because the SfM output already exists.

## What pairing changed

Matched runs are scored on the same eval frames, so the comparison is paired and
the per-frame difference is the quantity with a meaningful spread. `ns-eval`
reports only the mean and the marginal standard deviation, which is dominated by
how hard each frame is, and that difficulty is shared between the runs and
cancels in the differences. Re-running eval with per-frame output and testing
the differences directly changes several verdicts.

LPIPS, mean paired difference with a 95% interval, and how often the difference
kept its sign across frames:

| Comparison | n | Mean diff | 95% CI | Paired SD | Marginal SD | Same sign |
|---|---|---|---|---|---|---|
| seed off to on | 5 | -0.0810 | [-0.155, -0.007] | 0.060 | 0.070 | 5/5 |
| cap 100k to 250k | 5 | -0.0803 | [-0.097, -0.064] | 0.013 | 0.064 | 5/5 |
| cap 250k to 500k | 5 | -0.0505 | [-0.064, -0.037] | 0.011 | 0.050 | 5/5 |
| classic to antialiased | 5 | +0.0016 | [-0.004, +0.007] | 0.005 | 0.064 | 3/5 |
| prune 0.05, gaudi | 5 | +0.0007 | [+0.0004, +0.0010] | 0.0002 | 0.050 | 5/5 |
| prune 0.1, gaudi | 5 | +0.0042 | [+0.003, +0.005] | 0.0009 | 0.050 | 5/5 |
| prune 0.05, r2d2 | 7 | +0.0059 | [+0.004, +0.008] | 0.002 | 0.035 | 7/7 |
| prune 0.1, r2d2 | 7 | +0.0373 | [+0.029, +0.046] | 0.010 | 0.038 | 7/7 |

Three things fall out.

**Opacity pruning is not free.** At 0.05 it costs 0.0007 LPIPS on gaudi and
0.0059 on r2d2, and the sign holds on every frame of both scenes, with PSNR and
SSIM agreeing. The marginal spread is 70 times the gaudi effect, which is why it
read as noise. The trade is still worth taking for a median 28% size cut. The
verdict of "free" was not.

**PSNR and SSIM really are blind to the Gaussian budget.** This one survives
pairing and gets stronger for it. Across both cap steps the PSNR interval
contains zero and the sign splits 3/5, while LPIPS separates every step cleanly.
Pairing removed the excuse that the effect was hiding in the noise: it is not
there.

**Effects come in two kinds, and the marginal spread cannot tell them apart.**
Seeding moves LPIPS by 0.081 with a paired SD of 0.060, almost as large as the
marginal spread, so it helps some frames far more than others. Pruning at 0.05
moves it by 0.0007 with a paired SD of 0.0002, a consistent tax on every frame.
Judged against the marginal spread the first looks significant and the second
looks absent, when what actually separates them is homogeneity, not size.

One near miss is worth recording. Pairing the antialiased run against the
obvious partner made `rasterize_mode` look like a 0.083 LPIPS regression, which
would have overturned a correct result. The run predates the seed point cloud
landing in that scene directory, so the number was the seeding effect wearing a
different label. Timestamps caught it. Against its actual control the difference
is 0.0016 with the sign splitting 3/5, and `rasterize_mode` stays free.

## Would FID or KID do better?

Worth separating the premise first: LPIPS is not one of the metrics that works.
It scored 0.41, 0.34 and 0.51 in the three studies, at or below PSNR every time.
What worked was DISTS at 0.73 and the no-reference video models above 0.93. The
dividing line is not deep features against hand-built ones, since LPIPS and
DISTS are both deep-feature metrics separated by 0.4 in correlation.

FID and KID are a different kind of thing again. Both compare *distributions* of
features between two sets of images rather than scoring one image against
another, which gives them one property nothing else here has: they need no
correspondence between the sets. An A/B of two orbits has no per-frame ground
truth, since a novel camera path has no photograph, and that is exactly why
DISTS and CW-SSIM cannot be used on it. A set-level metric can compare the orbit
renders against the original capture frames without any pose in common, which
matches the delivery question directly. Does this exported asset still look like
photographs of this scene?

The one measurement available is MUGSQA's, which reports FID at 0.52 Spearman on
its main set and 0.77 on its additional set, second best of everything it tried
there. The gap between the two is informative. The main set spans 55 different
objects; the additional set fixes 3 objects and varies the reconstruction method.
A distribution metric compares content and quality at once, so when content
varies it measures mostly content. Fixed content with varying settings is our
case and is the regime where it did well.

Sample size is the obstacle. FID fits a Gaussian to each set and estimates a
2048-dimensional covariance, which on 11 eval frames has rank at most 10 and is
meaningless. The bias is well documented, and the part that matters is that it
depends on the model being scored, so evaluating two configurations at the same
small n does not cancel it. Chong and Forsyth propose extrapolating to infinite
samples to get around this; common practice is tens of thousands of images.

KID is the answer to that. It replaces the Fréchet distance with a
polynomial-kernel MMD that has an unbiased estimator and assumes nothing about
the distribution, which is what makes it usable at small n. Variance still falls
with sample size, but the bias does not depend on it, so a comparison at fixed
small n means something. Between the two, KID is the one to reach for here.

CMMD is the stronger version of the same idea. Jayasumana et al. argue FID fails
on three counts at once, with Inception features too narrow for varied content,
a normality assumption that does not hold, and poor sample complexity, and show
it contradicting human raters and reordering itself as sample size changes.
Their replacement keeps the MMD but swaps in CLIP embeddings and a Gaussian RBF
kernel. Unbiased, distribution-free, sample efficient, and available as
`clip-mmd`. If the goal is a feature-based distributional metric, this is the
current best version of it.

Three cautions before treating any of them as an answer.

They give one number per set, so they cannot be paired the way everything in the
table above was. Uncertainty has to come from bootstrapping over frames, and the
paired comparison that made the pruning effect visible has no analogue.

They are insensitive to exactly the errors a reconstruction makes. A render that
is plausible but geometrically wrong scores well, because the feature
distribution does not encode where anything is. This is a known failure in
view-synthesis evaluation, where distribution metrics improve while frame to
frame consistency gets worse.

The natural reference set is our own capture frames, which contain the tourists.
A model that correctly drops a transient gets penalised for not matching, the
same bias already documented for the held-out frames.

The honest recommendation is to test KID or CMMD as a companion, not a
replacement, and to put it through the same ladder as everything else. Render a
few hundred orbit frames per configuration, which costs nothing, use the capture
frames as the reference set, and require it to order a degradation ladder
correctly before asking it anything harder.

## What to measure instead

3DGS-VBench benchmarked five no-reference video quality models on compressed
splats and found DOVER, VSFA and FAST-VQA all above 0.93 Spearman, against 0.51
for the best of PSNR/SSIM/LPIPS. The paper describes no fine-tuning step for
these models, so the numbers appear to be off-the-shelf pretrained weights
applied to rendered videos. That is worth confirming against their code before
leaning on it.

If it holds, adopting it is cheap. These models take a video, need no reference,
and we already render orbit videos with `ns-render`. The change is one more step
after export, not a new benchmark.

Adopting it on the strength of separation alone would repeat the mistake this
document is about. A metric that moves when the configuration changes has shown
sensitivity, and sensitivity is what LPIPS already has. What we need is
agreement with a viewer, which takes stimuli whose perceptual ordering is
established before the metric is asked about them.

The proposed experiment, in order:

1. **Transfer check.** Build a ladder on one of our own scenes where the
   ordering is not in doubt: training truncated at 2k, 5k, 10k and 30k steps, or
   pruning at 25/50/75%, degradations large enough that anyone watching the
   orbits agrees which is worse. Require DOVER to reproduce that order. Passing
   shows the published 0.94 survives contact with our content and capture style;
   it does not yet show the metric is useful on close calls. Failing kills it
   outright, which is why this comes first and costs nothing.
2. **Paired comparisons on the contested decisions.** Three comparisons would
   agree with any metric one time in eight, so the set has to be big enough for
   agreement to mean something. The cleanup threshold supplies it for free: all
   15 Gaudi scenes have an uncropped export and a filtered one, and the cut
   ranges from 4.9% to 62%, which is a difficulty gradient rather than a single
   point. Add the cap_max pairs from the existing sweep.

   Present each pair as two orbits side by side, unlabelled, in randomised
   left-right order, and offer three responses: left, right, or no difference.
   Indifference has to be a legal answer. Forcing a choice between variants that
   look identical manufactures a label out of nothing, and "we cannot tell them
   apart" is both a likely outcome and a useful one, since it means ship the
   smaller file.

   Show every pair at least twice, separated. The repeat is not padding: it
   measures how often the rater agrees with themselves, which caps how much
   agreement any metric could show. A pair the rater flips on is a pair no
   metric can be scored against.
3. **Select on one half, validate on the other.** Split the pairs into a
   selection set and a held-out set before looking at any of them. Use the
   selection set to pick a metric, then score the winner once on the held-out
   set.

   The candidates have to be no-reference, because an A/B of two orbits has no
   ground truth to reference. A novel orbit path has no captured photo to
   compare against, so a full-reference metric has nothing to score. DISTS and
   CW-SSIM beat PSNR and LPIPS in the tables above and are useless here for that
   reason: scored A against B they give a symmetric distance with no direction,
   and scored against the unfiltered export as reference they hand it the win by
   construction. That leaves DOVER, VSFA, FAST-VQA and Q-Align, which score each
   orbit on its own. DISTS and CW-SSIM can only be tested on held-out frames
   where a real photo exists, which is a different experiment against different
   stimuli than the one a viewer judged. Count only pairs where the rater
   was self-consistent and expressed a preference, and fix the acceptance
   threshold in advance rather than after seeing the number. Adopting a metric
   on the same comparisons that chose it measures nothing.

   Three outcomes are worth naming ahead of time. A metric clears the threshold
   and gets wired in after `export`, reported alongside `ns-eval`. Nothing
   clears it, which means these calls are not metric-decidable for us and file
   size decides. Or the rater is mostly indifferent, which settles the
   underlying question without a metric: if 250k and 500k are indistinguishable
   on an orbit, ship 250k.

   One rater makes all of this suggestive rather than conclusive. It is still
   direct evidence about the decisions we actually make, which a published
   correlation on someone else's stimuli is not.
4. **Build stimuli only if 1 to 3 leave a real gap.** MUGSQA covers the input
   axes and released its data, so what would remain is attribute-based pruning
   and container quantisation at fixed training. That is a much smaller build
   than a full synthetic benchmark, and it needs its own subjective scores to be
   worth anything, which is the expensive part.

## Caveats

The correlations above are pooled across content, and our comparisons are not.
Pooling mixes in differences between object types that have nothing to do with
tuning, and the per-distortion breakdowns in both 3DGS-QA and MUGSQA do come out
higher than the pooled figure, so a within-scene comparison may well be easier
than 0.5 suggests. It may also be harder, because the settings we compare sit
much closer together than the stimuli in these datasets. Nobody has measured it.
Treat 0.5 as a reason to distrust close calls, not as an error rate for ours.

DBCNN at 0.88 and GSOQA at 0.77 are trained or cross-validated on the same
dataset they score. They are not drop-in metrics.

3DGS-QA reports FAST-VQA at 0.29 while 3DGS-VBench reports 0.93. The two
datasets contain different distortions and different content, and neither paper
explains the other's result. Treat the video-metric recommendation as promising
rather than settled until step 1 above runs on our own data.

## References

- 3DGS-VBench: [arXiv:2508.07038](https://arxiv.org/abs/2508.07038), data at
  [YukeXing/3DGS-VBench](https://github.com/YukeXing/3DGS-VBench)
- MUGSQA: [arXiv:2511.06830](https://arxiv.org/abs/2511.06830), data at
  [Solivition/MUGSQA](https://github.com/Solivition/MUGSQA)
- 3DGS-QA: [arXiv:2511.08032](https://arxiv.org/abs/2511.08032), data at
  [diaoyn/3DGSQA](https://github.com/diaoyn/3DGSQA)
- GS-QA: [arXiv:2502.13196](https://arxiv.org/abs/2502.13196)
- GGSC compression benchmark: [arXiv:2407.14197](https://arxiv.org/abs/2407.14197),
  code at [Qi-Yangsjtu/GGSC](https://github.com/Qi-Yangsjtu/GGSC)

Distribution metrics:

- KID: [arXiv:1801.01401](https://arxiv.org/abs/1801.01401), Bińkowski et al.,
  the unbiased MMD estimator FID lacks
- FID sample-size bias: [arXiv:1911.07023](https://arxiv.org/abs/1911.07023),
  Chong and Forsyth
- CMMD: [arXiv:2401.09603](https://arxiv.org/abs/2401.09603), Jayasumana et al.,
  CLIP features plus MMD, packaged as `clip-mmd`
- ImageNet class dependence of FID:
  [arXiv:2203.06026](https://arxiv.org/abs/2203.06026), Kynkäänniemi et al.
