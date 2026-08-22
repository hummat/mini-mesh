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
moves LPIPS by 0.0007 on `gaudi_fountain` and 0.0059 on `r2d2_new`, the same
sign on every frame of both, with PSNR and SSIM agreeing. It was called free
because the marginal spread is 0.05 and 0.035, which buried it. Whether a median
28% size saving is worth that is the trade the paired-comparison study exists to
settle, and this document cannot settle it: movement in an objective metric is
sensitivity, not a known change in what anyone sees. What is established is that
"free" was the wrong word and was reached the wrong way.

3DGS-QA measured content-blind random pruning at 25/50/75% and found it degrades
MOS smoothly. Our filter is attribute-based, targeting Gaussians the model
itself marked nearly transparent, which should cost less than random pruning at
the same rate. Nobody has measured that, and the 62% scenes remain the ones to
worry about.

**The container choice.** SPZ against SOG is a quantisation decision applied to
a fixed set of Gaussians. Measured on one cleaned 250k export (`gaudi_ceiling`,
224,367 Gaussians): 55.6 MB as PLY, 5.9 MB as SPZ, 2.6 MB as SOG, all carrying
three SH bands. Whether the 3.3 MB that SOG saves over SPZ costs anything a
viewer would see is exactly the kind of question the metrics above cannot
answer. GS-QA evaluates SOG, but as a reconstruction *method* with spherical
harmonics removed during training, not as a container applied afterwards.
Nothing published covers our version of the question.

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
kept its sign across frames. These intervals treat the frames as independent,
which the section below shows is wrong for a walkthrough. Whether it is wrong
here is a question about spacing, so it was measured rather than argued. See
"How independent are the eval frames" after the table. Three of these eight rows
were measured. On the two pruning rows at 0.05 the intervals come out 5 to 9%
too narrow; on the seeding row the interval should not be read as resolving
anything. The other five rows carry no measurement of their own and are assumed
to sit in the same range, which is untested.

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

### How independent are the eval frames

nerfstudio's fraction split takes the eval frames as the complement of an evenly
spaced training set, which lands them at 23, 46, 69, 92 and 115 on gaudi and
about 22 apart on r2d2. Spacing is not independence, so measure the correlation
of the thing being averaged: the paired per-frame LPIPS difference, computed on
every frame of the walkthrough in capture order.

It depends on which comparison, and by more than the spacing does:

| comparison            | rho at lag 1 | rho at eval spacing | below 0.1 at lag | ESS / n    |
| --------------------- | ------------ | ------------------- | ---------------- | ---------- |
| prune 0.05, gaudi     | 0.79         | +0.11 (lag 23)      | 31               | 6.5 / 112  |
| prune 0.05, r2d2      | 0.61         | -0.02 (lag 21)      | 5                | 25.8 / 147 |
| seed off to on, gaudi | 0.97         | +0.19 (lag 23)      | 25               | 4.6 / 112  |

Seeding is the slowly varying one, which fits what it does: it changes how well
the whole reconstruction resolves, so neighbouring views move together. Pruning
on r2d2 is nearly white by lag 5.

Summing the autocorrelation over the actual pairwise lags of the eval frames
gives the variance inflation for the mean. Estimated directly it comes out below
1 for all three, because the long lags return negative estimates. The longest of
those rest on 16 to 20 products, and the sample autocorrelation of any series
sums to -1/2 across all lags by construction, so the far tail is biased down. Clamping every
negative estimate to zero is the more cautious reading. Neither is a bound. The
positive estimates carry the same downward bias, so the true inflation can sit
above the clamped value, and at these lags nothing here pins it down. Read the
two as a sensitivity analysis:

| comparison             | as estimated | negatives to zero | width factor |
| ---------------------- | ------------ | ----------------- | ------------ |
| prune 0.05, gaudi      | 0.86         | 1.18              | up to 1.09   |
| prune 0.05, r2d2       | 0.85         | 1.10              | up to 1.05   |
| seed off to on, gaudi  | 0.76         | 1.31              | up to 1.15   |

At both values every row except seeding keeps its verdict, a 5 to 9% widening
that changes nothing. That is not the same as showing no verdict can move, since
the true inflation is not bounded above by either number. Seeding already fails
at the cautious value, and not by a comfortable margin either way. Its interval
reaches zero at a width factor of 1.095, which sits between the two: [-0.145,
-0.017] under the direct estimate and [-0.166, +0.004] under the clamped one.
The row should not be read as resolving anything, and the reason is dependence
rather than sample size.

A longer sequence is available, but it answers a different question. Rendering
both configurations over all 112 training views and moving-block bootstrapping
the mean gives -0.0714 with [-0.098, -0.045] at block length 20 and
[-0.102, -0.041] at 40, excluding zero at every block length tried, and the same
treatment resolves both pruning comparisons at every block length: +0.00054
[+0.00029, +0.00078] on gaudi and +0.00430 [+0.00395, +0.00463] on r2d2. Those
intervals need no effective sample size and no autocorrelation sum, because the
resampling carries the dependence itself.

They are not substitutes for the rows above. A training view is one the model
was fit to, so an effect can be large and precisely estimated there while doing
nothing for a pose the model never saw. Seeding is the case where that matters
most, since better initial geometry could plausibly show up as a tighter fit to
the views it was fitted on. The training-view interval is evidence about
training views; treating a narrow one as settling the held-out question would be
the estimand swapped under cover of a caveat.

So the honest position on seeding is three-part. On training views the effect is
large and resolved. On held-out views the five-frame test does not resolve it
under the sensitivity adjustment above, which is weaker than it sounds: that
adjustment borrows its autocorrelation from the training-view sequence, and a
set of poses the model was fitted to can differ from one it was not in
covariance as easily as in mean. Nothing here estimates dependence from held-out
frames, because five of them cannot. And the direction is the same at 10k and
30k steps, which is weak corroboration rather than strong, because both readings
come from the same five frames: the 0.468 to 0.387 gap at 10k is the -0.081
paired difference above written as levels, not a second measurement.

Settling it needs more held-out frames, which needs a pinned eval set rather
than a fraction split. That is the `eval_mode=filename` rerun already
outstanding for the frame-count experiment, and it would fix both.

Two caveats. A dependence-robust interval computed from the eval frames alone,
block or HAC, is not available at five and seven observations: it would need the
same long-lag autocorrelations, estimated from even less. A sensitivity analysis
is the ceiling, which is why the table cannot be repaired in place. And the
three comparisons measured here are the pruning pair on both scenes and the
seeding pair on gaudi; the cap and `rasterize_mode` rows have no autocorrelation
of their own and are assumed to sit inside the same range, which is untested.

Three things fall out.

**Opacity pruning produces a repeatable objective regression.** At 0.05 it moves
LPIPS by 0.0007 on gaudi and 0.0059 on r2d2, and the sign holds on every frame
of both scenes, with PSNR and SSIM agreeing. The marginal spread is 70 times the
gaudi effect, which is why it read as noise.

Calling that a perceptual cost would repeat the mistake this document is about.
Movement in these metrics is sensitivity, and their agreement with viewers runs
around 0.5, so 0.0007 LPIPS is a measured change in a number and not a known
change in what anyone sees. Whether it is worth a median 28% size cut is exactly
the trade the paired-comparison experiment exists to settle, and until that runs
the honest statement is that the filter has a small consistent effect on three
objective metrics. The earlier verdict of "free" was wrong for a different and
simpler reason: it was never measured.

**PSNR and SSIM respond far more weakly to the Gaussian budget than LPIPS.**
Across both cap steps the PSNR interval contains zero and the sign splits 3/5,
while LPIPS separates every step cleanly. Measured against each metric's own
paired noise, the 100k to 250k step moves LPIPS by 6.1 standard deviations, SSIM
by 0.77, and PSNR by 0.001. PSNR and SSIM do not belong in the same sentence
here: PSNR's response is about four orders of magnitude weaker than LPIPS's,
while SSIM's is merely too weak to resolve on five frames.

That is the defensible claim, and "blind" is not. Five frames failing to reject
zero is not evidence of no effect, and the PSNR interval spans plus or minus
0.24 dB, which is wide enough to contain changes that would matter. Saying the
effect is absent needs an equivalence bound declared in advance and an interval
that fits inside it, neither of which exists here.

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
is 0.0016 with the sign splitting 3/5 and an interval running from -0.004 to
+0.007. That does not make `rasterize_mode` free, which is the same error this
document objects to two paragraphs above: effects as large as either endpoint
are still compatible with five frames. The honest statement is that the
comparison is unresolved, and calling it free needs an equivalence bound set in
advance with the whole interval inside it.

## Would FID or KID do better?

Worth separating the premise first: LPIPS is not one of the metrics that works.
It scored 0.41, 0.34 and 0.51 in the three studies. Two of those report PSNR as
well, and LPIPS lands 0.11 below it in MUGSQA and 0.01 above it in 3DGS-VBench,
so it buys nothing over the metric it was meant to improve on.
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
looks like the delivery question. Does this exported asset still look like
photographs of this scene? That framing is what motivated the rest of this
section, and it does not survive it.

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

KID answers that on paper. It replaces the Fréchet distance with a
polynomial-kernel MMD that has an unbiased estimator and assumes nothing about
the distribution, which is what makes it usable at small n. Variance still falls
with sample size, but the bias does not depend on it, so a comparison at fixed
small n should mean something. On that reasoning I expected KID to be the one to
reach for. The measurements below disagree, and the reason is variance rather
than bias.

CMMD is the stronger version of the same idea. Jayasumana et al. argue FID fails
on three counts at once, with Inception features too narrow for varied content,
a normality assumption that does not hold, and poor sample complexity, and show
it contradicting human raters and reordering itself as sample size changes.
Their replacement keeps the MMD but swaps in CLIP embeddings and a Gaussian RBF
kernel: distribution-free, sample efficient, and available as `clip-mmd`.

One detail matters before leaning on the unbiasedness argument twice. The
estimator Google published, which `clip-mmd` vendors verbatim, is the
minimum-variance form of Gretton et al.'s Eq. (5). It averages the kernel matrix
including its diagonal, so it is the biased V-statistic, not the unbiased one
that makes KID safe at small n. The docstring argues the two are almost
identical, citing the proof of Lemma 6 in the same paper. That argument does not
carry on its own, because the diagonal term each configuration contributes
depends on its own within-set similarities and so need not cancel between two of
them. Measured, it does cancel here; the numbers are under "What the intervals
assume". KID is still the one with the cleaner claim.

Three cautions before treating any of them as an answer.

They give one number per set, so uncertainty has to come from bootstrapping over
frames rather than from a per-frame difference. The pairing does survive that,
as long as it is built in: two configurations rendered at the same orbit poses
and scored against the same capture set share both sets of indices, so a
replicate should resample the frame indices and the reference indices once and
recompute the *difference* under that shared resampling. Bootstrapping the two
estimates independently throws away the covariance, which is the thing that made
a 0.0007 effect visible in the first place.

They are insensitive to exactly the errors a reconstruction makes. A render that
is plausible but geometrically wrong scores well, because the feature
distribution does not encode where anything is. This is a known failure in
view-synthesis evaluation, where distribution metrics improve while frame to
frame consistency gets worse.

The natural reference set is our own capture frames, which contain the tourists.
A model that correctly drops a transient gets penalised for not matching, the
same bias already documented for the held-out frames.

### What happened when I ran them

I ran all three rather than leaving the question open. Every training view of
each configuration, rendered at full resolution without loss and scored against
the capture photographs, on two scenes. CMMD uses CLIP ViT-L/14-336 features with a single
bicubic resize to 336 by 336; FID and KID use the standard 2048-d Inception
pool3 features. Uncertainty comes from bootstrap replicates that resample the
frame indices once per replicate and recompute the *difference* under that
shared resampling, in blocks of 20 consecutive frames for the reason set out
under "What the intervals assume" below. The ladder is the opacity pruning
threshold at 0, 0.00392, 0.01, 0.02, 0.05 and 0.1.

The first rung is a free calibration check, and not by luck. 0.00392 is 1/255,
which is the cutoff gsplat's rasterizer already applies: `alpha < 1.f / 255.f`
then `continue`, in `rasterize_to_pixels_fwd.cu`. A Gaussian's alpha at a pixel
is its opacity scaled by a factor no greater than one, so a Gaussian whose
opacity sits below that line is skipped at every pixel and contributes to no
image. Pruning at 1/255 cannot change a render, and both scenes duly produce
byte-identical images to the unpruned run. The two configurations are the same
model as far as anything downstream can tell. All three return exactly zero on it with a
zero-width interval, which is what a correctly paired bootstrap has to return on
identical inputs and what independent bootstrapping of the two estimates would
not have returned. KID only does so after the fix described below; on its
standard protocol it returned 0.30.

#### What each one did

The rungs to watch are the fine ones, because the section below measures what
actually separates them: 61 dB on gaudi and 68 dB on r2d2 between the unpruned
render and the 0.01 rung, 53 and 57 dB at 0.02. The images there differ, but
barely. Whether an estimator ought to resolve a difference that small is a
question about how much difference matters, which nothing in this document
settles.

| rung    | gaudi FID | gaudi KID x1000 | gaudi CMMD | r2d2 FID | r2d2 KID x1000 | r2d2 CMMD |
| ------- | --------- | --------------- | ---------- | -------- | -------------- | --------- |
| 0       | 62.68     | 16.553          | 0.4554     | 35.83    | 4.214          | 0.6907    |
| 0.00392 | 62.68     | 16.553          | 0.4554     | 35.83    | 4.214          | 0.6907    |
| 0.01    | 62.65     | 16.515          | 0.4563     | 35.82    | 4.209          | 0.6913    |
| 0.02    | 62.63     | 16.460          | 0.4563     | 35.78    | 4.150          | 0.6984    |
| 0.05    | 63.33     | 16.507          | 0.4695     | 37.29    | 4.649          | 0.7730    |
| 0.1     | 68.10     | 18.200          | 0.5312     | 47.86    | 8.384          | 1.0172    |

All three pass the null rung exactly, returning zero with a zero-width interval
on the pair that renders byte-identical images.

Steps, with an interval excluding zero marked R:

| gaudi step      | ΔFID                      | ΔKID x1000                | ΔCMMD                        |
| --------------- | ------------------------- | ------------------------- | ---------------------------- |
| 0 → 0.00392     | +0.000 [+0.000, +0.000]   | +0.000 [+0.000, +0.000]   | +0.0000 [+0.0000, +0.0000]   |
| 0.00392 → 0.01  | -0.028 [-0.088, +0.030]   | -0.038 [-0.065, +0.010]   | +0.0009 [-0.0002, +0.0023]   |
| 0.01 → 0.02     | -0.024 [-0.172, +0.100]   | -0.055 [-0.198, +0.035]   | -0.0000 [-0.0023, +0.0023]   |
| 0.02 → 0.05     | +0.702 [+0.253, +1.339] R | +0.047 [-0.316, +0.762]   | +0.0132 [+0.0099, +0.0184] R |
| 0.05 → 0.1      | +4.772 [+4.105, +6.951] R | +1.694 [+0.929, +3.961]   | +0.0618 [+0.0470, +0.0862] R |

| r2d2 step       | ΔFID                         | ΔKID x1000                | ΔCMMD                        |
| --------------- | ---------------------------- | ------------------------- | ---------------------------- |
| 0 → 0.00392     | +0.000 [+0.000, +0.000]      | +0.000 [+0.000, +0.000]   | +0.0000 [+0.0000, +0.0000]   |
| 0.00392 → 0.01  | -0.001 [-0.013, +0.012]      | -0.005 [-0.017, +0.008]   | +0.0006 [-0.0007, +0.0018]   |
| 0.01 → 0.02     | -0.049 [-0.116, +0.009]      | -0.059 [-0.118, -0.024]   | +0.0071 [+0.0048, +0.0096] R |
| 0.02 → 0.05     | +1.511 [+1.054, +2.246] R    | +0.499 [+0.135, +1.081]   | +0.0746 [+0.0624, +0.0876] R |
| 0.05 → 0.1      | +10.577 [+9.925, +14.690] R  | +3.735 [+2.937, +6.391] R | +0.2442 [+0.2039, +0.2937] R |

The coarse end belongs to FID and CMMD. Both resolve 0.02 to 0.05 and 0.05 to
0.1 on both scenes, and agree on direction throughout. KID resolves one of those
four, r2d2's 0.05 to 0.1, and the intervals shown carry the R only where the
percentile and basic constructions agree, which costs KID two of the three it
had under the percentile alone. The weakest of the resolved cases is FID on
gaudi's 0.02 to 0.05 step, where the interval's near end still sits a third of
the way to the estimate.

The fine end resolves once, for CMMD, on r2d2's 0.01 to 0.02 step at +0.0071
with [+0.0048, +0.0096]. FID spans zero there, and on the other three fine steps
every metric does.

That step used to read as a contradiction. KID gives -0.059 on the same images
and the same frames, and its interval excluded zero too, so two estimators were
resolving one step in opposite directions. The disagreement was never a fact
about the images. It came from the paired cross terms below, and once those are
removed KID's interval covers zero and only CMMD is left saying anything. What
survives is a weaker statement worth keeping: a polynomial-kernel distance on
Inception features and an RBF distance on CLIP features can move in opposite
directions on the same change without either being wrong, so at most one of
them tracks any single notion of quality, and this data cannot say which, or
whether either does.

An earlier version of this section had FID resolving gaudi's 0.00392 to 0.01
step as an improvement, and I read that as the metric misbehaving. It was the
JPEG encoder, and it vanished when the renders were written losslessly. Worth
recording, because a resolved interval on an artifact is the exact failure this
document is about, produced while writing it.

#### A flaw in the standard KID protocol

KID needed fixing before any of the above could be read. The usual protocol
averages the unbiased MMD over random subsets of the two feature sets, and
drawing those subsets independently for the two configurations under comparison
injects noise that the pairing cannot cancel, because the two runs never see the
same subsets. On the null rung, where the render sets are byte-identical, the
first pass scored 15.76 against 16.07, a difference of 0.30 where the truth is
exactly zero and against a ladder spanning 1.7 end to end. The estimator is
unbiased on the whole set, so the subsetting can be dropped outright. The null
rung then returns exactly zero and the frame bootstrap is the only source of
uncertainty left. Every KID number above is computed that way, and anyone
comparing two configurations with KID should do the same, or at minimum share
the subset draws between them.

#### The two sets are not independent samples

KID and the unbiased CMMD check both estimate a distance between two
distributions, and both are unbiased for it when the two sets are independent
samples. These sets are not. Render i and photograph i are the same camera pose,
so k(render_i, photo_i) is not a draw from the product of the marginals, and the
two-sample estimator keeps all n of those terms inside a cross sum of n squared.
The resulting bias is O(1/n) and depends on the configuration being scored,
which is the combination a difference between configurations cannot cancel.

Dropping the paired terms costs one line and settles the size. On the levels it
is enormous for KID. Gaudi's ladder moves from 16.55 to 20.25 and r2d2's from
4.21 to 7.56, because a render and its own photograph are far more alike than a
render and someone else's pose. CMMD's unbiased check moves about 2%, from
0.4394 to 0.4490 and from 0.6751 to 0.6861.

On the differences it is small and uneven. Every CMMD step moves by under 1% and
not one classification changes, under either interval construction. KID's move
by up to 10%: r2d2's 0.02 to 0.05 goes from +0.499 to +0.448 and its 0.05 to 0.1
from +3.735 to +3.521. The correction also shrinks as the rungs coarsen instead
of holding constant, which is the configuration dependence showing up directly.

One verdict does not survive it. KID's r2d2 0.01 to 0.02 step, the one place the
fine end resolved for it, reads [-0.096, -0.001] with the paired terms in and
[-0.097, +0.005] with them out. That was the disagreement with CMMD, and it was
an artifact of the estimator. A step is marked R above only when it excludes
zero under both interval constructions and both treatments of the cross terms.
That leaves KID resolving one of the eight steps, r2d2's 0.05 to 0.1, and leaves
the fine end to CMMD alone.

FID is untouched. It uses each set's own mean and covariance and never forms a
cross-set kernel, so there is no paired term in it to remove.

#### What the intervals assume

Every interval above comes from a moving-block bootstrap with a block length of
20, which resamples runs of consecutive frames instead of individual ones. The
frames are consecutive poses along a walkthrough, so neighbouring views share
most of their content, and an i.i.d. resample treats them as independent
observations and returns an interval narrower than the data supports.

Enough of the procedure to rerun it. Each replicate draws ceil(n/L) block
starts uniformly from 0 to n-1, takes L consecutive indices from each with
wraparound past the end of the sequence, concatenates them and truncates back
to n. One index set per replicate indexes the configuration under test, the one
it is compared against, and the reference set alike, so the pairing survives the
resample. The reported difference is the statistic on the observed sample. The
mean over the replicates is a different quantity for a nonlinear statistic,
estimating the resampling expectation rather than the difference that was
measured, and it would make the point estimate depend on the replicate count and
the seed. The interval is the 2.5th and 97.5th percentile of the replicate
differences. R marks a step that excludes zero under every construction and
estimator variant the sections above try, which for the set-level metrics means
both interval constructions and both treatments of the paired cross terms. The
set-level
tables use 400 replicates, the per-frame LPIPS ones 2000, and the walkthrough
comparison quoted earlier 20000. Every generator is seeded at 0, and the
set-level runs draw the whole ladder from one of them in sequence, so those
intervals are reproducible as a set rather than one step at a time. Their
endpoints move in the last quoted digit between generators in any case. FID uses
the low-rank Frechet identity described below, KID the unbiased estimator on the
full set with no subset averaging, and CMMD the V-statistic accumulated in
float64.

Which point estimate gets reported is not a formality here. On r2d2's 0.05 to
0.1 step the replicate mean sits at 12.00 FID against 10.58 observed and at 4.40
KID against 3.74, so the percentile interval is dragged along with it and the
observed value lands near its lower end rather than in the middle. CMMD moves by
under three percent on the same step.

That shift belongs to the resampling rather than to the sampling uncertainty,
and a percentile interval carries it into the verdict. The basic interval
removes it by reflecting the replicates through the observed value, and the two
constructions disagree on three steps, all of them KID: gaudi's 0.05 to 0.1 and
r2d2's 0.02 to 0.05 lose their exclusion of zero, gaudi's 0.00392 to 0.01 gains
one. FID and CMMD keep every classification under both. So R marks a step whose
interval excludes zero under both constructions, and the three that disagree are
left unresolved. Even that is generous in one place: r2d2's 0.01 to 0.02 clears
under the basic interval by 0.00013 on a step of -0.059. The LPIPS ladder needs
none of this, since the bootstrap expectation of a sample mean is the sample
mean and there is no shift to remove.

How much it costs splits the metrics in two, and the split is the useful part of
the check. Interval width at block length 20 over width at block length 1:

| statistic                         | ratio        |
| --------------------------------- | ------------ |
| LPIPS, a mean of per-frame values | 3.0 to 3.8   |
| FID, KID and CMMD, set-level      | 0.89 to 1.72 |

The three set-level metrics are not separable from each other on this: FID runs
0.89 to 1.61, KID 1.06 to 1.67, CMMD 0.91 to 1.72, all overlapping. What
separates them from LPIPS is that a mean of per-frame values is exactly what
correlated neighbours inflate, while a statistic computed from the whole
resampled set carries less of it. So block resampling costs the
export-referenced LPIPS ladder below a great deal of width and this section
almost none.

Width is not the whole story, and stopping at 20 was a choice, so the set-level
metrics got the same sweep out to 100. Their widths peak between 5 and 40
depending on the step and shrink from 60 on, the same collapse the LPIPS ladder
shows, so a long block is not a conservative block here either. Out to 40 no
verdict moves with the block length. Under the percentile construction the 0.02
to 0.05 and 0.05 to 0.1 steps stay resolved for every metric on both scenes
except KID on gaudi's 0.02 to 0.05, which stays unresolved, and r2d2's 0.01 to
0.02 stays resolved for CMMD at every length tried, and for KID at every length
until the paired cross terms come out.

Crossing that sweep with the interval construction sorts the three metrics:
CMMD holds every coarse verdict under both constructions at every block length,
FID holds all of them except gaudi's 0.02 to 0.05 at block lengths 5 and 10,
and KID's coarse verdicts move with the block length, the construction, or
both. Its gaudi 0.05 to 0.1 step, for one, excludes zero under the basic
interval at block length 1 and from 60 up, and not between.

Past 40 the collapse starts manufacturing resolutions instead: r2d2's 0.01 to
0.02 turns resolved for FID at 60, gaudi's 0.01 to 0.02 for KID at 100.

The rest of the fine end is worse than the tables make it look. Gaudi's 0.00392
to 0.01 KID interval has an endpoint sitting on zero and changes verdict at
almost every block length tried: resolved at 1, 10, 30 and everything from 60
up, unresolved at 5, 20 and 40. That step is not measuring anything. The coarse
conclusions for FID and CMMD survive both the block length and the construction,
KID's do not, and the fine ones apart from r2d2's 0.01 to 0.02 were never
conclusions.

It does not overturn the LPIPS ladder, and the widths do not run away either.
At 20 they were still climbing, 16 to 22% over block length 10, which left the
question of where they stop. Pushing the ladder out to block lengths of 30, 40,
60, 80 and 100 answers it: every rung peaks at 40, 7 to 17% wider than at 20,
and falls back after. The fall is forced by the resampling rather than by the
data. A wrapped block of length L covers a fixed fraction of the sequence
whatever its start, so as L approaches n every replicate converges on the
full-sample mean and the interval has to collapse.

That makes 40 the widest this resampling can go, which is not the same as a
bound on the uncertainty, so two checks that do not depend on the sweep. The
Politis-White automatic block length lands between 17 and 23 on all eight
non-degenerate rungs, below the peak rather than beyond it. A Newey-West
variance with a Bartlett kernel, which does not resample at all, gives widths
within 14% of the length-40 bootstrap on every rung, and wider than it on one.
Three different treatments of the dependence agree to about a tenth.

What none of them do is bound dependence that 112 and 147 frames cannot show.
On simulated AR(1) series of the same length and first-order correlation the
Politis-White selector recovers 44 to 60% of the block length the closed form
asks for, so it is known to run short in this regime, and doubling what it
selects lands back at the swept peak. The reported intervals stay at block
length 20, where the set-level metrics were also measured.

FID needed a second fix for an unrelated reason. Its bootstrap had been running
25 replicates, because the textbook Frechet term needs the square root of a
2048 by 2048 matrix, and 25 draws cannot support a 2.5th percentile. It does not
need that square root. With n frames and n well below 2048 both covariances have
rank at most n-1, so the nonzero eigenvalues of the product live in an n by n
matrix built from the centred feature blocks, and the trace term is the sum of
their square roots. The identity agrees with torchmetrics to three parts in a
million, with the residual a constant offset that cancels in a difference, and
400 replicates now cost less than 25 did.

Two classifications moved between them, both from resolved to unresolved. KID
resolved gaudi's 0.00392 to 0.01 step under the i.i.d. bootstrap, where -0.038
carried [-0.072, -0.001], and does not under blocks, where the same -0.038
carries [-0.065, +0.010]. FID resolved r2d2's 0.01 to 0.02 step on 25
replicates, where -0.049 carried [-0.098, -0.001], and does not on 400, where it
carries [-0.116, +0.009]. The estimate cannot move, since it is the difference
on the observed sample either way; both intervals grew past zero, which is what
the fine end looks like once the interval stops being optimistic.

CMMD needed a third. The implementation here is Google's, which uses the biased
V-statistic rather than the unbiased U-statistic, and its bias is not a constant
that a difference can be relied on to cancel: the excess over the U-statistic is
one minus the mean off-diagonal kernel similarity, divided by n, once per set,
and that quantity depends on the configuration being scored. On this ladder it
does not move. The excess is 0.0160 on gaudi and 0.0156 on r2d2, the same to
four decimals across all six rungs, and the configuration-dependent factor
varies only in the fifth decimal. Recomputing every step with the unbiased
estimator shifts none of them by more than 0.00015 and leaves every
classification standing: r2d2's 0.01 to 0.02 step reads +0.0071 with
[+0.0048, +0.0096] biased and +0.0071 with [+0.0047, +0.0095] unbiased.

Checking that turned up a fourth thing, which has nothing to do with either
objection. CMMD is 1000 times the difference of three kernel means that all sit
within 0.001 of 1.0, so in float32 the cancellation quantises the answer at
1000 times 2^-23, or 0.00012. Two independent float32 runs of the same
computation on the same images disagreed by up to 0.00048, and against float64
each is out by up to 0.00022. Every CMMD number in this document is now
accumulated in float64. The steps mostly survived the change, because the shared
reference term cancels between the two configurations, but the fine ones are
small enough that they need not have: gaudi's 0.00392 to 0.01 step is 0.0010,
eight of those quantisation units. Four decimals on a float32 CMMD value are
three decimals of number and one of rounding.

#### How much of each is the sample count

Each estimator on the unpruned run, at four frame counts:

| frames | gaudi FID | gaudi KID | gaudi CMMD | frames | r2d2 FID | r2d2 KID | r2d2 CMMD |
| ------ | --------- | --------- | ---------- | ------ | -------- | -------- | --------- |
| 28     | 75.46     | 1.528     | 0.4377     | 36     | 43.44    | -6.431   | 0.6206    |
| 56     | 70.06     | 14.060    | 0.4842     | 73     | 38.58    | 1.164    | 0.6754    |
| 84     | 67.34     | 14.559    | 0.4561     | 110    | 37.60    | 3.887    | 0.7154    |
| 112    | 62.68     | 16.553    | 0.4554     | 147    | 35.83    | 4.214    | 0.6907    |

FID falls monotonically as frames are added in both scenes, which is the bias
Chong and Forsyth describe. The drift is 12.8 points on gaudi against a ladder
whose whole range is 5.4, so the number cannot be read on its own and two
configurations evaluated at different frame counts cannot be compared at all.
The steps above survive because the shared bootstrap cancels the part of that
bias the two runs have in common. How much that is stays unmeasured. The null
rung shows the cancellation is exact when the two configurations are identical,
which is the easy case; the bias depends on the feature distribution, and two
configurations that differ do not have to share all of it.

KID is worse in a different way. A single draw at 36 frames puts the r2d2 run at
-6.4, a negative squared distance, which an unbiased estimator is entitled to
produce and which supports no ordering whatsoever. Unbiased in expectation is
not the same as usable from one draw at this size. CMMD wanders least in
relative terms but still moves more between 28 and 56 frames than the entire
0.02 to 0.05 step it is being asked to detect. Its rows below the full frame
count are float32 and carry the 0.0002 noted above, which is two orders of
magnitude under the drift being discussed.

Three limits apply to all of the above. These are training views, which the
model was fit to, so they understate every degradation. The reference set is our
own capture frames, tourists included, so a model that correctly drops a
transient is penalised for it. And an interval spanning zero means the test
could not resolve that step at this sample size, which is not the same as the
step being free.

#### What to take from this

No opinion scores exist for this ladder, and nothing here supplies a substitute.
The fine rungs render 53 to 68 dB apart, which says the images barely differ, and
it is tempting to read a resolved interval there as a false positive. That
reading does not hold. The images do differ, so an estimator separating them is
detecting something real; a narrow interval around a tiny effect is what
sensitivity looks like. Calling it an error would need an equivalence bound
declared in advance and an interval that fits inside it, which is the same thing
this document demands before anyone calls PSNR blind. No such bound exists here.

So the fine end ranks nobody. FID and KID resolve nothing there, CMMD resolves
one step, and which of those is the right behaviour depends on a threshold
nobody has set.

What does separate them needs no labels, because it is about the estimators
rather than the images. Two things, and the first version of one of them was
wrong.

FID's absolute level falls 12.8 points between 28 and 112 frames, more than
twice the range of the whole ladder, so it cannot be read as a number and two
configurations scored at different frame counts cannot be compared at all. The
paired steps survive because the shared bootstrap cancels the part of that drift
the two runs have in common, with the caveat above on how much that is. Nothing
rescues the level.

The second is discriminability under matched samples. Each metric's own
bootstrap supplies its sampling deviation, on the same frames under the same
resampling, so the ratio of a step to that deviation compares estimators in
spite of their different units. On the four steps where the renders genuinely
differ:

| step             | FID  | KID  | CMMD  |
| ---------------- | ---- | ---- | ----- |
| gaudi 0.02→0.05  | 2.53 | 0.17 | 6.10  |
| gaudi 0.05→0.1   | 6.57 | 2.19 | 6.18  |
| r2d2 0.02→0.05   | 4.97 | 2.07 | 11.59 |
| r2d2 0.05→0.1    | 8.70 | 4.24 | 10.66 |

CMMD leads in three of the four and KID trails in all four, while FID takes the
largest step on gaudi's coarsest. That is the comparison this conclusion
needed. An earlier version rested it on KID returning -6.4 at 36 frames, which
does not support anything: a negative value is exactly what an unbiased
U-statistic is entitled to produce, it bars reading that point estimate as an
absolute distance, and it leaves untouched the paired differences the tables
above are built from. CMMD's estimator is the biased V-statistic and nonnegative
by construction, so never going negative is a property of its formula rather
than evidence of stability.

The fine steps are left out of that table on purpose. A higher ratio there would
mean only that an estimator separates images that barely differ, and whether
that is a virtue is the question no bound has settled.

FID and CMMD resolve both coarse steps on both scenes and agree on direction,
which is the regime where the choice between those two stops mattering. KID does
not join them. It fails gaudi's 0.02 to 0.05 outright, at +0.047 with
[-0.316, +0.762] and unresolved at every block length tried, and loses gaudi's
0.05 to 0.1 and r2d2's 0.02 to 0.05 once the interval stops carrying its own
resampling bias.

The larger conclusion is that this line of attack was aimed at a problem we do
not have. Set-level metrics earn their keep when nothing corresponds between the
thing being scored and any reference. Scene reconstruction always has a capture,
and for the questions this project actually asks, which are about transforms
applied after training, there is a reference better suited than the photographs:
the pre-transform export. Render it and the transformed asset at the same poses
and the comparison is exact, paired per frame, free of transients, and available
along the delivery camera path rather than only where someone stood with a
camera.

That measures the right quantity for a delivery decision, which is how far a
transform moves the image away from the asset we would otherwise ship. It cannot
say whether the move is an improvement, because the reference wins by
construction, and it cannot say whether anyone would notice. Both still need the
study below. What it does supply is the thing the photo-referenced ladder never
had: an answer that is checkable against a fact rather than against another
metric.

## Scoring against the export instead of the photographs

The section above ends by arguing that the pre-transform export is the better
reference for anything applied after training. That is cheap to test, since the
renders already exist. Each rung scored against the unpruned render at the same
poses, per frame, LPIPS with a 95% interval on the mean.

One thing the poses are not: an orbit. The argument for this reference includes
that it works along the delivery camera path, and that remains an argument.
These numbers come from the capture poses, because those are the renders already
on disk. Whether a transform moves the image more or less at viewpoints away
from the capture is a question this table does not answer, and pruning is a
plausible place for it to differ, since a Gaussian that is edge-on from the
capture is not edge-on from everywhere. Rendering the same rungs along an orbit
would settle it and costs one more render pass.

| threshold | gaudi LPIPS vs unpruned      | PSNR dB | r2d2 LPIPS vs unpruned       | PSNR dB |
| --------- | ---------------------------- | ------- | ---------------------------- | ------- |
| 0         | 0.00000 [0.00000, 0.00000]   | inf     | 0.00000 [0.00000, 0.00000]   | inf     |
| 0.00392   | 0.00000 [0.00000, 0.00000]   | inf     | 0.00000 [0.00000, 0.00000]   | inf     |
| 0.01      | 0.00005 [0.00005, 0.00006]   | 61.02   | 0.00002 [0.00002, 0.00002]   | 68.01   |
| 0.02      | 0.00030 [0.00027, 0.00033]   | 53.41   | 0.00031 [0.00028, 0.00034]   | 57.02   |
| 0.05      | 0.00322 [0.00291, 0.00353]   | 43.20   | 0.00775 [0.00715, 0.00834]   | 42.14   |
| 0.1       | 0.02032 [0.01871, 0.02191]   | 34.01   | 0.05406 [0.05050, 0.05780]   | 31.59   |

These are lossless renders. The first attempt wrote JPEG at quality 95, the
setting hardcoded in the throwaway script that rendered these frames, and
produced 0.00085 and 0.00038 at the 0.01 rung, seventeen and nineteen times the
truth. Re-encoding each lossless frame at q95 and scoring it against its own
source puts the encoder's error at 0.00795 LPIPS and 48.5 dB on r2d2, 0.00597
and 46.0 dB on gaudi. None of that comes from the rendering: the JPEG pass is
byte for byte identical to those re-encodings on all 147 and 112 frames, so both
passes drew the same pixels and the encoder is the only thing left between them.
The repository's own orbit renderer defaults to quality 100, which is a
different setting and not a safer one. Encoding the same frames across the range
gives LPIPS of 0.01941, 0.01084, 0.00795, 0.00802 and 0.00843 on r2d2 at q80,
q90, q95, q98 and q100, and 0.01954, 0.00983, 0.00597, 0.00430 and 0.00396 on
gaudi. PSNR climbs with the setting on both scenes, 44.7 to 50.4 dB and 41.7 to
49.4 dB, and LPIPS does not: on r2d2 it bottoms out at q95 and rises again, so
the q100 default costs 6% more LPIPS than q95 while writing files 2.2 times the
size. The two scenes disagree about the direction, which is the point. Against a
photograph the number is nothing, since renders sit around 22 dB from those, and
against another render at 61 to 68 dB it is overwhelming. The artifacts
mostly cancel between two nearly identical images and decorrelate as the images
separate, so the contamination grows with the rung instead of sitting under
everything as a constant floor: seventeen times at 0.01, six at 0.02, and still
1.7 at 0.05. Write PNG for any render-against-render comparison.

Every problem the distribution metrics had at the fine end disappears. The pose
question is not one of them: those were scored on the same capture poses, and
the difference is that they could not have been scored anywhere else, since the
photographs only exist where someone stood. This comparison could be, and has
not been. The ladder is monotone in both scenes. No neighbouring pair of
intervals overlaps. The identity rung returns exactly zero with infinite PSNR,
which is a fact rather than a
calibration hope. Where FID and KID both invert on both scenes and the three of
them together resolve one fine step out of eight, this separates all five rungs
in both scenes, and the separation survives every treatment of the dependence
tried. The tightest neighbouring gap is 2.6 times the wider of the two intervals
at the block length where the resampling is widest, 2.7 under a Newey-West
variance at a bandwidth of 40, and no pair comes closer at any block length from
1 to 100. Closing the tightest of those gaps takes a factor of 2.6 in width,
against the tenth that separates the three treatments. CMMD does better than the
other two at the fine end: it orders both ladders correctly, and it is the only
one of the three that resolves r2d2's 0.01 to 0.02 step.

The reason is not that LPIPS is a better metric than CMMD. It is that the
comparison is paired at the level of individual frames against an exact
reference, so two of the three things the set metrics estimate stop being
estimated: the reference is the pre-transform render rather than a photograph,
and the quantity is a per-frame difference rather than a distance between two
fitted distributions. The third remains. The mean over poses is still a sample
average over 112 correlated cameras, which is why it carries a bootstrap
interval and why the choice of poses matters. The question changed, and the
easier question has a much better answer, but it is not an exact one.

What it buys is a real decision. Both scenes start from a 1M cap. Pruning at
0.05 leaves 628k Gaussians on gaudi and 619k on r2d2, a cut of roughly 38% in
both, and moves the image at the capture poses by 0.0032 and 0.0078 LPIPS at 42
to 43 dB.
Pruning at 0.1 leaves 446k and 324k, cuts of 55% and 68%, and moves it by 0.020
and 0.054 at around 32 dB.

The fine rungs come out very small indeed: 61 dB on gaudi and 68 dB on r2d2 at
0.01. That says nothing about the threshold actually being shipped. The step
from 0.01 to 0.05 is where almost all of the deviation and almost all of the
size saving happen, and 0.0032 and 0.0078 LPIPS at 42 dB is a magnitude, not a
verdict. What this replaces is the previous state of affairs, where the number
was unmeasured and the threshold was set by assertion. Whether it is small
enough to ship is still the study's question, now asked about a known
quantity.

Two things it still cannot do. The unpruned export wins by construction, so this
can never report that pruning improved anything, only how far it moved. And a
0.0032 LPIPS deviation is not a statement about what a viewer would notice,
which remains the open question the study below is meant to close.

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
   Record which configuration the answer names rather than which side. The order
   is drawn again at every showing, so a rater who prefers the same asset three
   times will have clicked different sides, and a rater who clicks the same side
   every time will have named different assets. Scoring sides would reject the
   first and accept the second, which is backwards. Scored by configuration a
   fixed-side habit looks like guessing, which is what it is. Indifference has
   to be a legal answer. Forcing a choice between variants that
   look identical manufactures a label out of nothing, and "we cannot tell them
   apart" is both a likely outcome and a useful one, since it means ship the
   smaller file.

   Show every pair three times, separated. The repeats are not padding: they
   measure how often the rater agrees with themselves, which caps how much
   agreement any metric could show. Two showings cannot establish that. A
   rater guessing on a pair they see no difference in still repeats the same
   answer about a third of the time when there are three responses to choose
   from, and every one of those accidents would enter the next step as a
   label. Requiring all three showings to agree drops that floor to one in
   nine, and what it filters out is concentrated in the close pairs, which are
   the ones the exercise is about. Report the raw agreement rate next to the
   floor. A rate near it on the close pairs says the rater cannot separate
   them at all, which answers the question without a metric and means no
   metric can be validated on them either. A pair the rater flips on is a pair
   no metric can be scored against.
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
   stimuli than the one a viewer judged. Score a pair only when all three of its
   showings named the same configuration, which is the same bar step 2 sets, and
   score every pair that clears it, including the ones called identical all
   three times. Dropping those would validate a candidate on the pairs that were
   easy to call and then wire it in for the close ones, which are the pairs it
   exists to settle. A unanimous "no difference" is a label like any other, so require
   the metric to reproduce it: fit a deadband on the selection set wide enough
   to contain the pairs called identical, then on the held-out set ask the
   preference pairs to fall outside the band with the correct sign and the
   indifference pairs to fall inside it. Report the two rates separately, and
   fix both acceptance thresholds in advance rather than after seeing the
   numbers. A candidate that gets the obvious pairs right and pushes the
   indifferent ones outside its band has earned the obvious pairs only, and
   should be used on that class alone. Adopting a metric on the same
   comparisons that chose it measures nothing.

   Three outcomes are worth naming ahead of time. A metric clears the threshold,
   which makes it a candidate rather than a default. Nothing clears it, which
   means these calls cannot be automated with these candidates. Or the rater is
   mostly indifferent, which settles the underlying question without a metric:
   if 250k and 500k are indistinguishable on an orbit, ship 250k.

   The second outcome is not a licence to ship the smaller file. A metric can
   fail by mispredicting preferences the rater expressed unanimously, and those
   preferences do not evaporate when the metric that was supposed to reproduce
   them does. Where a pair drew a stable preference, follow it. File size
   decides the pairs the rater could not separate and the pairs never rated,
   and pairs that matter and stay unresolved are an argument for rating more of
   them rather than for a tiebreaker.

   With one rater all three are statements about that rater, and none is a
   statement about viewers. Repeats measure whether a rater agrees with
   themselves. A consistent but idiosyncratic preference produces exactly the
   pattern a metric can be fitted to, an unusual detection threshold fails a
   metric that would work for other people, and one insensitive rater's
   indifference is not evidence that anybody else would miss the difference.
   Nothing in the design separates any of those from the population case. So
   the experiment as described settles what we default to and nothing wider,
   and each outcome should be written down that way. Treating any of the three
   as a claim about viewers needs a second rater, recruited independently and
   scoring the same held-out pairs, and that goes double for wiring a metric in
   after `export` for every asset we ship. Short of it the winner stays a
   diagnostic reported next to `ns-eval` rather than a criterion anything is
   decided on.
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

Resampling under dependence:

- Politis and White, "Automatic Block-Length Selection for the Dependent
  Bootstrap", Econometric Reviews 23(1), 53-70, 2004, with the correction in
  Patton, Politis and White, Econometric Reviews 28(4), 372-375, 2009
  ([PDF](https://public.econ.duke.edu/~ap172/Politis_White_2004.pdf),
  [correction](https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf))
- Newey and West, "A Simple, Positive Semi-Definite, Heteroskedasticity and
  Autocorrelation Consistent Covariance Matrix", Econometrica 55(3), 703-708,
  1987
